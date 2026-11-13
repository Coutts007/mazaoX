from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """`page` / `page_size` pagination returning the API spec envelope."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "data": data,
                "pagination": {
                    "page": self.page.number,
                    "page_size": self.page.paginator.per_page,
                    "total_items": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                },
            }
        )

    def get_paginated_response_schema(self, schema):
        return {"type": "object", "properties": {"data": schema, "pagination": {"type": "object"}}}
