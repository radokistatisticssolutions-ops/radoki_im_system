from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_alter_notification_notif_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notif_type',
            field=models.CharField(
                choices=[
                    ('assignment_new',        'New Assignment Posted'),
                    ('assignment_graded',     'Assignment Graded'),
                    ('assignment_reviewed',   'Assignment Reviewed'),
                    ('assignment_resubmit',   'Needs Resubmission'),
                    ('assignment_submitted',  'Assignment Submitted'),
                    ('lesson_new',            'New Lesson Available'),
                    ('module_new',            'New Module Added'),
                    ('lesson_complete',       'Lesson Completed'),
                    ('resource_uploaded',     'New Resource Uploaded'),
                    ('quiz_posted',           'New Quiz Posted'),
                    ('quiz_result',           'Quiz Result'),
                    ('quiz_passed',           'Quiz Passed'),
                    ('live_session_scheduled','New Live Session Scheduled'),
                    ('service_new',           'New Service Request'),
                    ('service_status',        'Service Request Update'),
                    ('coupon_created',        'New Coupon Created'),
                    ('coupon_applied',        'Coupon Applied to Order'),
                    ('referral_completed',    'Referral Completed'),
                    ('referral_reward_ready', 'Referral Reward Available'),
                    ('referral_claimed',      'Referral Reward Claimed'),
                    ('payment_approved',      'Enrollment Approved'),
                    ('course_enrolled',       'New Student Enrolled'),
                    ('certificate_ready',     'Certificate Ready for Download'),
                    ('general',               'General'),
                ],
                default='general',
                max_length=30,
            ),
        ),
    ]
