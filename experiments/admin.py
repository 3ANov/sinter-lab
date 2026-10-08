from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import CoefficientSet, ComputationRun, Experiment, Material


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


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'researcher', 'coefficients', 'created_at')
    list_filter = ('coefficients__material',)
    search_fields = ('title', 'researcher__username')
    autocomplete_fields = ('researcher', 'coefficients')
    readonly_fields = ('coefficient_snapshot', 'material_name_snapshot', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('coefficients',)
        return self.readonly_fields


@admin.register(ComputationRun)
class ComputationRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'experiment', 'researcher', 'point_count', 'created_at', 'result_links')
    list_select_related = ('experiment', 'experiment__researcher')
    list_filter = ('created_at', 'experiment__coefficients__material')
    search_fields = ('experiment__title', 'experiment__researcher__username')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = tuple(field.name for field in ComputationRun._meta.fields if field.name != 'results') + ('point_count', 'result_links')

    @admin.display(description='Исследователь', ordering='experiment__researcher__username')
    def researcher(self, obj):
        return obj.experiment.researcher

    @admin.display(description='Точек')
    def point_count(self, obj):
        return len(obj.results)

    @admin.display(description='Результаты')
    def result_links(self, obj):
        if not obj.pk:
            return '—'
        return format_html(
            '<a href="{}">Графики и таблицы</a> · <a href="{}">Excel</a>',
            reverse('experiments:results', args=[obj.pk]),
            reverse('experiments:export_excel', args=[obj.pk]),
        )

    def has_add_permission(self, request):
        return False
