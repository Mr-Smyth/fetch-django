from django.shortcuts import render, reverse, get_object_or_404
from django.views.generic.base import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# For ajax step 1
from django.http import JsonResponse
from django.core import serializers

from .models import Post, Comment, Category
from .forms import CommentForm


class PageContextMixin(object):
    page_title = None

    def get_context_data(self, **kwargs):
        context = super(PageContextMixin, self).get_context_data(**kwargs)
        context['page_title'] = self.page_title
        return context


class Home(PageContextMixin, ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    ordering = '-pub_date'
    paginate_by = 3
    page_title = 'Home'


@method_decorator(login_required, name='dispatch')
class Dashboard(View):
    def get(self, request, *args, **kwargs):
        view = Home.as_view(
            template_name='blog/admin_page.html',
            paginate_by=4
        )
        return view(request, *args, **kwargs)


class PostDisplay(PageContextMixin, SingleObjectMixin, View):
    model = Post
    page_title = 'Detail'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.view_count += 1
        self.object.save()
        post = self.get_context_data(object=self.object)
        return render(request, 'blog/post_detail.html', post)

    def get_context_data(self, **kwargs):
        context = super(PostDisplay, self).get_context_data(**kwargs)
        context['comments'] = Comment.objects.filter(post=self.get_object())
        context['form'] = CommentForm
        return context


@method_decorator(login_required, name='dispatch')
class PostComment(FormView):
    form_class = CommentForm

    # --------------------------------------------
    #
    # Ajax - step 3 - add form invalid method

    def form_invalid(self, form):
        # check if header in request includes ajax (XML - see js)
        if self.request.is_ajax():
            # if it is an ajax request return the errors from the form
            return JsonResponse({"error": form.errors}, status=400)
        else:
            return JsonResponse({"error": "Invalid form and request"},
                                status=400)

    # --------------------------------------------

    # --------------------------------------------
    #
    # Ajax - step 2
    #
    # check is request an ajax request
    def form_valid(self, form):
        if self.request.is_ajax():
            form.instance.by = self.request.user
            post = Post.objects.get(pk=self.kwargs['pk'])
            form.instance.post = post
            # put form.save() into the variable comment_instance
            comment_instance = form.save()
            # serialize the new comment into json format. 2 args
            # first arg is the format - (json)
            # second arg is the save form and part of query set
            ser_comment = serializers.serialize("json", [comment_instance, ])

            # then return the serialized response of the serialized comment
            # and a status 200
            return JsonResponse({"new_comment": ser_comment}, status=200)
        else:
            # else return a nice big error and status 400 if it is not an
            # ajax request
            return JsonResponse({"error": "Error occured during request"},
                                status=400)

        # --------------------------------------------

        # No need for a get_success_url

class PostDetail(View):
    def get(self, request, *args, **kwargs):
        view = PostDisplay.as_view()
        return view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        view = PostComment.as_view()
        return view(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class PostCreate(CreateView):
    model = Post
    fields = ('title', 'category', 'content')

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.save()
        return super(PostCreate, self).form_valid(form)


@method_decorator(login_required, name='dispatch')
class PostUpdate(UpdateView):
    model = Post
    fields = ('title', 'category', 'content')


@method_decorator(login_required, name='dispatch')
class PostDelete(DeleteView):
    model = Post
    success_url = reverse_lazy('dashboard')


class PostCategory(ListView):
    model = Post
    template_name = 'blog/post_category.html'

    def get_queryset(self):
        self.category = get_object_or_404(Category, pk=self.kwargs['pk'])
        return Post.objects.filter(category=self.category)

    def get_context_data(self, **kwargs):
        context = super(PostCategory, self).get_context_data(**kwargs)
        context['category'] = self.category
        return context