from django.urls import path

from . import views

app_name = "story"

urlpatterns = [
    path("", views.StoryListView.as_view(), name="story-list"),
    path("<uuid:story_id>/session/", views.CurrentSessionNodeView.as_view(), name="session-current"),
    path("<uuid:story_id>/session/choice/", views.SubmitChoiceView.as_view(), name="session-choice"),
    path("<uuid:story_id>/session/profile/", views.ProfileView.as_view(), name="session-profile"),
    path("<uuid:story_id>/session/reflection/", views.ReflectionView.as_view(), name="session-reflection"),
    path("<uuid:story_id>/replay/", views.ReplayView.as_view(), name="story-replay"),
    path("<uuid:story_id>/compare/", views.RunComparisonView.as_view(), name="story-compare"),
]
