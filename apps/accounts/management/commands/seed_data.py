from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.flocks.models import Flock
from apps.production.models import EggProduction
from apps.feed.models import Feed, FeedStock
from apps.customers.models import Customer
from apps.suppliers.models import Supplier

class Command(BaseCommand):
    help = "Create KukuFarm demo data"
    def handle(self, *args, **kwargs):
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={"email":"admin@kukufarm.co.tz","first_name":"KukuFarm","last_name":"Administrator","is_staff":True,"is_superuser":True}
        )
        if created:
            user.set_password("admin123")
            user.save()
        else:
            user.is_staff = True; user.is_superuser = True; user.set_password("admin123"); user.save()
        UserProfile.objects.update_or_create(user=user, defaults={"role":"admin","job_title":"System Administrator"})

        f1, _ = Flock.objects.get_or_create(code="FL-001", defaults={
            "name":"Layers","breed":"ISA Brown","source":"Local Supplier",
            "arrival_date":date.today()-timedelta(weeks=42),
            "initial_quantity":1800,"current_quantity":1760,"age_weeks":42,
            "status":"active","house":"House A"
        })
        f2, _ = Flock.objects.get_or_create(code="FL-002", defaults={
            "name":"Layers Batch 2","breed":"Lohmann Brown","source":"Local Supplier",
            "arrival_date":date.today()-timedelta(weeks=32),
            "initial_quantity":1000,"current_quantity":990,"age_weeks":32,
            "status":"active","house":"House B"
        })
        for name, typ, qty, cost in [
            ("Layers Mash","Layer Feed",1500,1800),
            ("Growers Mash","Grower Feed",800,1600),
            ("Starter Feed","Starter Feed",500,2000),
        ]:
            feed, _ = Feed.objects.get_or_create(name=name, defaults={"feed_type":typ,"unit_cost":cost,"minimum_stock":200})
            FeedStock.objects.get_or_create(feed=feed, defaults={"quantity":qty})
        EggProduction.objects.get_or_create(flock=f1, date=date.today(), defaults={"eggs_collected":1450,"broken_eggs":20,"rejected_eggs":5,"trays":48.33})
        for name, phone in [("ABC Hotel","0712000000"),("Dodoma Market","0713000000"),("Mambo Retail","0714000000")]:
            Customer.objects.get_or_create(name=name, defaults={"phone":phone})
        for name, phone in [("Kuku Feed Suppliers","0755000000"),("Farm Pharmacy","0766000000")]:
            Supplier.objects.get_or_create(name=name, defaults={"phone":phone})
        self.stdout.write(self.style.SUCCESS("Seed complete. Login: admin / admin123"))
