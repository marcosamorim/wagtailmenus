from django.db import models
from django.utils.translation import ugettext_lazy as _

from django.core.exceptions import ValidationError
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey

from wagtail.wagtailcore.models import Page
from wagtail.wagtailadmin.edit_handlers import (
    FieldPanel, PageChooserPanel, MultiFieldPanel, FieldRowPanel, InlinePanel)
from wagtail.wagtailcore.models import Orderable

from .managers import MenuItemManager
from .panels import menupage_settings_panels


class MenuPage(Page):
    repeat_in_subnav = models.BooleanField(
        verbose_name=_("repeat in sub-navigation"),
        help_text=_(
            "If checked, a link to this page will be repeated alongside it's "
            "direct children when displaying a sub-navigation for this page."
        ),
        default=False,
    )
    subnav_menu_text = models.CharField(
        verbose_name=_('link text for sub-navigation item'),
        max_length=255,
        blank=True,
        help_text=_(
            "e.g. 'Section home' or 'Overview'. If left blank, the page title "
            "will be used."
        )
    )

    settings_panels = menupage_settings_panels

    class Meta:
        abstract = True


class MenuItem(models.Model):
    allow_subnav = False

    link_page = models.ForeignKey(
        'wagtailcore.Page',
        verbose_name=_('link to an internal page'),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    link_url = models.CharField(
        max_length=255,
        verbose_name=_('link to a custom URL'),
        blank=True,
        null=True,
    )
    link_text = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Must be set if you wish to link to a custom URL."),
    )
    url_append = models.CharField(
        verbose_name=_("append to URL"),
        max_length=255,
        blank=True,
        help_text=(
            "Use this to optionally append a #hash or querystring to the "
            "above page's URL.")
    )

    objects = MenuItemManager()

    class Meta:
        abstract = True
        verbose_name = _("menu item")
        verbose_name_plural = _("menu items")

    def relative_url(self, current_site):
        try:
            url = self.link_page.relative_url(current_site)
        except AttributeError:
            url = self.link_url
        return url + self.url_append

    @property
    def menu_text(self):
        if self.link_page:
            return self.link_text or self.link_page.title
        return self.link_text

    def clean(self, *args, **kwargs):
        super(MenuItem, self).clean(*args, **kwargs)

        if self.link_url and not self.link_text:
            raise ValidationError({
                'link_text': [
                    _("This must be set if you're linking to a custom URL."),
                ]
            })

        if not self.link_url and not self.link_page:
            raise ValidationError({
                'link_url': [
                    _("This must be set if you're not linking to a page."),
                ]
            })

        if self.link_url and self.link_page:
            raise ValidationError(_(
                "You cannot link to both a page and URL. Please review your "
                "link and clear any unwanted values."
            ))

    def __unicode__(self):
        return self.menu_text

    panels = (
        PageChooserPanel('link_page'),
        FieldPanel('url_append'),
        FieldPanel('link_text'),
        FieldPanel('link_url'),
    )


class MainMenu(ClusterableModel):
    site = models.OneToOneField('wagtailcore.Site', related_name="main_menu")

    class Meta:
        verbose_name = _("main menu")
        verbose_name_plural = _("main menu")

    def __unicode__(self):
        return 'For %s' % (self.site.site_name or self.site)

    panels = (
        FieldPanel('site'),
        InlinePanel('menu_items', label=_("Menu items")),
    )


class FlatMenu(ClusterableModel):
    site = models.ForeignKey(
        'wagtailcore.Site',
        related_name="flat_menus")
    title = models.CharField(
        max_length=255,
        help_text=_("For internal reference only."))
    handle = models.SlugField(
        max_length=100,
        help_text=_(
            "Used to reference this menu in templates etc. Must be unique "
            "for the selected site."))
    heading = models.CharField(
        max_length=255,
        blank=True,
        help_text=_(
            "If supplied, appears above the menu when rendered."))

    class Meta:
        unique_together = ("site", "handle")
        verbose_name = _("flat menu")
        verbose_name_plural = _("flat menus")

    def __unicode__(self):
        return u'%s (%s)' % (self.title, self.handle)

    panels = (
        MultiFieldPanel(
            heading=_("Settings"),
            children=(
                FieldRowPanel(
                    classname='label-above',
                    children=(
                        FieldPanel('site', classname="col12"),
                        FieldPanel('title', classname="col6"),
                        FieldPanel('handle', classname="col6"),
                        FieldPanel('heading', classname="col12"),
                    )
                ),
            )
        ),
        InlinePanel('menu_items', label=_("Menu items")),
    )


class MainMenuItem(Orderable, MenuItem):
    menu = ParentalKey('MainMenu', related_name="menu_items")

    allow_subnav = models.BooleanField(
        default=True,
        verbose_name=_("allow sub-navigation for this page"),
    )
    panels = MenuItem.panels + (
        FieldPanel('allow_subnav'),
    )


class FlatMenuItem(Orderable, MenuItem):
    menu = ParentalKey('FlatMenu', related_name="menu_items")
