from rest_framework import filters


class CompanyFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if request.user and request.user.is_authenticated and queryset.model.__name__ != 'Company':
            queryset = queryset.filter(company_id=request.user.company_id)

        return queryset

