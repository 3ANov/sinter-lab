from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import CoefficientSet, Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)


@admin.register(CoefficientSet)
class CoefficientSetAdmin(admin.ModelAdmin):
    list_display = ('material', 'version', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5')
    list_filter = ('material',)
    search_fields = ('material__name',)
    autocomplete_fields = ('material',)

