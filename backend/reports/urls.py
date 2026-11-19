from django.urls import path
from .views import SummaryView, ExportView
urlpatterns = [path("summary/", SummaryView.as_view()), path("export/", ExportView.as_view())]
