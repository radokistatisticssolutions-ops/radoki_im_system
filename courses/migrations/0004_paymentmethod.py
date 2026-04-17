# Generated manually for PaymentMethod model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0003_course_curriculum_course_duration_course_mode_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method_type', models.CharField(choices=[('MPESA', 'M-Pesa'), ('MIXX_BY_YAS', 'MIXX by YAS'), ('AIRTEL', 'Airtel Money'), ('AZAMPESA', 'AzaM pesa'), ('HALOTEL', 'Halotel')], help_text='Payment method type', max_length=15)),
                ('lipa_namba', models.CharField(help_text='Lipa Namba (phone number)', max_length=20)),
                ('merchant_id', models.CharField(help_text='Merchant ID', max_length=100)),
                ('merchant_name', models.CharField(help_text='Name of the merchant', max_length=200)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_methods', to='courses.course')),
            ],
            options={
                'unique_together': {('course', 'method_type')},
            },
        ),
    ]
