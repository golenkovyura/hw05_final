from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

from posts.models import Group, Post, Follow, User
from posts.forms import PostForm, CommentForm


def pagginator(page_number, post_list):
    paginator = Paginator(post_list, settings.NUM_POSTS)
    return paginator.get_page(page_number)


def index(request):
    template = 'posts/index.html'
    post_list = Post.objects.select_related('group', 'author')
    context = {
        'page_obj': pagginator(request.GET.get('page'), post_list),
    }
    return render(request, template, context)


def group_posts(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author')
    context = {
        'group': group,
        'page_obj': pagginator(request.GET.get('page'), post_list),
    }
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    author = get_object_or_404(User, username=username)
    following = request.user.is_authenticated and request.user.follower.filter(
        author=author).exists()
    post_list = author.posts.select_related('group')
    context = {
        'author': author,
        'page_obj': pagginator(request.GET.get('page'), post_list),
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'posts/post_detail.html'
    post = get_object_or_404(
        Post.objects.select_related('group', 'author'),
        pk=post_id
    )
    comments = post.comments.select_related('author')
    context = {
        'post': post,
        'comments': comments,
        'form': CommentForm()
    }
    return render(request, template, context)


@login_required
def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        temp_form = form.save(commit=False)
        temp_form.author = request.user
        temp_form.save()
        return redirect('posts:profile', temp_form.author)
    context = {
        'form': form,
    }
    return render(request, template, context)


def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(
        Post.objects.select_related('group', 'author'),
        pk=post_id
    )
    if post.author != request.user:
        return redirect('users:login')
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = get_object_or_404(Post, pk=post_id)
        comment.author = request.user
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(
        author__following__user=request.user).select_related('group', 'author')
    context = {
        'page_obj': pagginator(request.GET.get('page'), post_list),
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    follow_user = get_object_or_404(User, username=username)
    if follow_user != request.user:
        Follow.objects.get_or_create(user=request.user, author=follow_user)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    follow_author = get_object_or_404(User, username=username)
    get_object_or_404(
        Follow,
        user=request.user,
        author=follow_author
    ).delete()
    return redirect('posts:profile', username)
