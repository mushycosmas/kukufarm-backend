from django.contrib import admin
from .models import Feed, FeedPurchase, FeedStock
admin.site.register([Feed, FeedPurchase, FeedStock])
