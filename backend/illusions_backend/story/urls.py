from django.urls import path

from . import views

app_name = "story"

urlpatterns = [
    path("current/", views.CurrentNodeView.as_view(), name="current-node"),
    path("choice/", views.SubmitChoiceView.as_view(), name="submit-choice"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
