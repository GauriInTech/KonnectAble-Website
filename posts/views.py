from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Like, Comment
from django.http import JsonResponse


@login_required
def posts_list(request):
    # POST requests create a post; AJAX returns JSON, otherwise redirect to dashboard
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')  # read uploaded image

        if content or image:
            post = Post.objects.create(user=request.user, content=content, image=image)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'id': post.id,
                    'user': post.user.username,
                    'content': post.content,
                    'image_url': post.image.url if post.image else None,
                    'created_at': post.created_at.isoformat(),
                })
        return redirect('accounts_home')

    # For GET, show the posts only on the dashboard; redirect here
    return redirect('UserDashboard')


@login_required
def like_post(request, post_id):
    post = Post.objects.get(id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            "likes_count": post.like_set.count(),
            "liked": created,
            "post_id": post.id
        })
    else:
        return redirect('accounts_home')


@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        post = Post.objects.get(id=post_id)
        text = request.POST.get('text')
        if text:
            Comment.objects.create(post=post, user=request.user, text=text)
    return redirect('accounts_home')


@login_required
def delete_post(request, post_id):
    post = Post.objects.get(id=post_id)
    if post.user == request.user:  # Only owner can delete
        post.delete()
    return redirect('accounts_home')
