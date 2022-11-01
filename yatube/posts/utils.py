from django.core.paginator import Paginator


def paginator(request, posts, count_obj):
    paginator = Paginator(posts, count_obj)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
