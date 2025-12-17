from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Like, Comment
from django.http import JsonResponse


@login_required
def posts_list(request):
    if request.method == 'POST':
        content = request.POST.get('content')
        image = request.FILES.get('image')  # read uploaded image

        # Allow posting text only, image only, or both
        if content or image:
            Post.objects.create(
                user=request.user,
                content=content,
                image=image
            )
            return redirect('posts')

    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'posts/posts.html', {'posts': posts})


@login_required
def like_post(request, post_id):
    post = Post.objects.get(id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return JsonResponse({
        "likes_count": post.like_set.count(),
        "liked": created,
        "post_id": post.id
    })


@login_required
def add_comment(request, post_id):
    if request.method == 'POST':
        post = Post.objects.get(id=post_id)
        text = request.POST.get('text')
        if text:
            Comment.objects.create(post=post, user=request.user, text=text)
    return redirect('posts')


@login_required
def delete_post(request, post_id):
    post = Post.objects.get(id=post_id)
    if post.user == request.user:  # Only owner can delete
        post.delete()
    return redirect('posts')
