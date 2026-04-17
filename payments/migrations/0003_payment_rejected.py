from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_payment_rejection_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='rejected',
            field=models.BooleanField(default=False),
        ),
    ]
