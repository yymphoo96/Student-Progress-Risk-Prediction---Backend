from django.urls import path
from .views import CSVUploadView

urlpatterns = [
    path('assessments/upload-csv/', CSVUploadView.as_view(), name='csv-upload'),
]
