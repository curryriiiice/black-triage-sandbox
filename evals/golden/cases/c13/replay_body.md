<!-- triage-replay: {"case_id": "c13", "original_created_at": "2026-04-29T22:29:25Z", "original_author_association": "NONE"} -->
So I came across this that bothers me a lot that after reaching max line length all the arguments inside a method goes to next line. 

I want only the last one goes to the next line like this:

```
#####This is a long comment. This should be wrapped to fit within 80 characters.
urlpatterns = [
    path("<int:pk>/", ArticleDetailView.as_view(), name="article_detail"),
    path("<int:pk>/edit/", ArticleUpdateView.as_view(), name="article_edit"),
    path("<int:pk>/delete/", ArticleDeleteView.as_view(), 
          name="article_delete"),
    path("new/", ArticleCreateView.as_view(), name="article_new"),
    path("", ArticleListView.as_view(), name="article_list"),
]
```

instead of:

```
#####This is a long comment. This should be wrapped to fit within 80 characters.
urlpatterns = [
    path("<int:pk>/", ArticleDetailView.as_view(), name="article_detail"),
    path("<int:pk>/edit/", ArticleUpdateView.as_view(), name="article_edit"),
    path(
        "<int:pk>/delete/", ArticleDeleteView.as_view(), name="article_delete"
    ),
    path("new/", ArticleCreateView.as_view(), name="article_new"),
    path("", ArticleListView.as_view(), name="article_list"),
]

```


How can I force the first one in black? Any solutions?
