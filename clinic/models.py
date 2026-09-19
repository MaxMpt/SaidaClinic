from django.db import models


class Service(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=80, default="")
    description = models.TextField(blank=True, default="")
    duration_min = models.IntegerField()
    price = models.IntegerField()
    prepay_amount = models.IntegerField(default=0)
    prepay_percent = models.IntegerField(default=0)
    prep_text = models.TextField(blank=True, default="")
    aftercare_text = models.TextField(blank=True, default="")
    indications = models.TextField(blank=True, default="")
    contraindications = models.TextField(blank=True, default="")
    result_text = models.TextField(blank=True, default="")
    reactions_text = models.TextField(blank=True, default="")
    image_key = models.CharField(max_length=40, default="still")
    invasive = models.BooleanField(default=False)
    recommend_days = models.IntegerField(default=90)
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]

    def __str__(self):
        return self.title


class Appointment(models.Model):
    client_key = models.CharField(max_length=64, db_index=True)
    client_name = models.CharField(max_length=200)
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    day = models.DateField(db_index=True)
    start_min = models.IntegerField()
    end_min = models.IntegerField()
    status = models.CharField(max_length=24, default="confirmed")
    comment = models.TextField(blank=True, default="")
    source = models.CharField(max_length=24, default="app")
    prepay_required = models.IntegerField(default=0)
    prepay_paid = models.IntegerField(default=0)
    hold_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(blank=True, default="")
    admin_note = models.TextField(blank=True, default="")
    price = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["day", "status"])]


class TimeBlock(models.Model):
    day = models.DateField()
    start_min = models.IntegerField(default=0)
    end_min = models.IntegerField(default=1440)
    reason = models.CharField(max_length=120, default="Выходной")


class OpenDay(models.Model):
    day = models.DateField(primary_key=True)


class DayHours(models.Model):
    day = models.DateField(primary_key=True)
    start_min = models.IntegerField()
    end_min = models.IntegerField()


class Waitlist(models.Model):
    client_key = models.CharField(max_length=64)
    client_name = models.CharField(max_length=200)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    desired_date = models.DateField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Setting(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    value = models.TextField(blank=True, default="")


class Notification(models.Model):
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    appointment_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)


class Review(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE)
    client_key = models.CharField(max_length=64)
    rating = models.IntegerField()
    text = models.TextField(blank=True, default="")
    photos = models.TextField(default="[]")
    service_title = models.CharField(max_length=200, default="")
    created_at = models.DateTimeField(auto_now_add=True)


class Loyalty(models.Model):
    client_key = models.CharField(max_length=64, primary_key=True)
    stamps = models.IntegerField(default=0)
    points = models.IntegerField(default=0)


class Affirmation(models.Model):
    body = models.TextField()
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)


class CareCategory(models.Model):
    title = models.CharField(max_length=120)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class CareProduct(models.Model):
    category = models.ForeignKey(CareCategory, on_delete=models.CASCADE, related_name="products")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    indications = models.TextField(blank=True, default="")
    contraindications = models.TextField(blank=True, default="")
    composition = models.TextField(blank=True, default="")
    price = models.IntegerField(default=0)
    photo = models.CharField(max_length=300, blank=True, default="")
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class Client(models.Model):
    telegram_id = models.CharField(max_length=32, primary_key=True)
    username = models.CharField(max_length=64, blank=True, default="")
    first_name = models.CharField(max_length=120, default="Гость")
    last_name = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=16, default="client")
    intake = models.JSONField(default=dict)
    intake_done = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
