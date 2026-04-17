from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from decimal import Decimal

from .models import ReferralLink, Referral, ReferralReward, ReferralSettings
from courses.models import Course, Enrollment, Coupon

User = get_user_model()


class ReferralSettingsTestCase(TestCase):
    """Test ReferralSettings singleton model"""
    
    def setUp(self):
        self.settings = ReferralSettings.get_settings()
    
    def test_singleton_creation(self):
        """Test that ReferralSettings follows singleton pattern"""
        settings1 = ReferralSettings.get_settings()
        settings2 = ReferralSettings.get_settings()
        self.assertEqual(settings1.id, settings2.id)
        self.assertEqual(ReferralSettings.objects.count(), 1)
    
    def test_default_settings(self):
        """Test default configuration values"""
        # Delete existing and create fresh
        ReferralSettings.objects.all().delete()
        settings_obj = ReferralSettings.get_settings()
        self.assertEqual(settings_obj.is_active, True)
        self.assertEqual(settings_obj.reward_type, ReferralReward.RewardType.DISCOUNT_PERCENTAGE)
        self.assertEqual(settings_obj.reward_validity_days, 90)
        self.assertEqual(settings_obj.max_rewards_per_student, 0)  # 0 = unlimited
        self.assertIsNotNone(settings_obj.updated_at)
    
    def test_settings_update(self):
        """Test updating settings"""
        settings = ReferralSettings.get_settings()
        original_days = settings.reward_validity_days
        settings.reward_validity_days = 60
        settings.save()
        
        updated = ReferralSettings.get_settings()
        self.assertEqual(updated.reward_validity_days, 60)
        self.assertNotEqual(updated.reward_validity_days, original_days)


class ReferralLinkTestCase(TestCase):
    """Test ReferralLink model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='referrer',
            email='referrer@test.com',
            password='testpass123'
        )
    
    def test_referral_link_creation(self):
        """Test creating a referral link"""
        link = ReferralLink.objects.create(
            student=self.user,
            code=ReferralLink.generate_code(),
            referral_url='http://testserver/signup/?ref=TEST'
        )
        self.assertEqual(link.student, self.user)
        self.assertIsNotNone(link.code)
        self.assertEqual(len(link.code), 8)
        self.assertEqual(link.total_referrals, 0)
        self.assertEqual(link.successful_referrals, 0)
    
    def test_code_generation_uniqueness(self):
        """Test that generated codes are unique"""
        codes = set()
        for _ in range(10):
            code = ReferralLink.generate_code()
            self.assertNotIn(code, codes)
            codes.add(code)
        
        self.assertEqual(len(codes), 10)
    
    def test_code_length(self):
        """Test that generated codes have correct length"""
        for _ in range(5):
            code = ReferralLink.generate_code()
            self.assertEqual(len(code), 8)
            self.assertTrue(code.isupper())
    
    def test_referral_url_property(self):
        """Test referral_url field"""
        link = ReferralLink.objects.create(
            student=self.user,
            code='TEST1234',
            referral_url='http://testserver/signup/?ref=TEST1234'
        )
        self.assertIn('TEST1234', link.referral_url)
        self.assertIn('ref=', link.referral_url)
    
    def test_get_conversion_rate_zero(self):
        """Test conversion rate with no referrals"""
        link = ReferralLink.objects.create(
            student=self.user,
            code=ReferralLink.generate_code()
        )
        self.assertEqual(link.get_conversion_rate(), 0)
    
    def test_get_conversion_rate_calculation(self):
        """Test conversion rate calculation uses live DB query, not stale counters."""
        link = ReferralLink.objects.create(
            student=self.user,
            code=ReferralLink.generate_code(),
            referral_url='http://testserver/signup/?ref=TEST'
        )
        referred_user = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )

        # Referral is PENDING — conversion rate should be 0%
        referral = Referral.objects.create(
            referral_link=link,
            referred_user=referred_user,
            status=Referral.Status.PENDING
        )
        self.assertEqual(link.get_conversion_rate(), 0)

        # Advance referral to REWARD_PENDING (payment confirmed, reward created)
        referral.status = Referral.Status.REWARD_PENDING
        referral.save(update_fields=['status'])

        # Conversion rate should now be 100% (1 paid out of 1 total)
        self.assertEqual(link.get_conversion_rate(), 100)
    
    def test_one_per_student_constraint(self):
        """Test that each student can have only one ReferralLink"""
        link1 = ReferralLink.objects.create(
            student=self.user,
            code=ReferralLink.generate_code()
        )
        
        # Try to create another for same student - should fail
        with self.assertRaises(Exception):
            ReferralLink.objects.create(
                student=self.user,
                code=ReferralLink.generate_code()
            )


class ReferralTestCase(TestCase):
    """Test Referral model"""
    
    def setUp(self):
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@test.com'
        )
        self.referred = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )
        self.referral_link = ReferralLink.objects.create(
            student=self.referrer,
            code=ReferralLink.generate_code(),
            referral_url='http://testserver/signup/?ref=TEST'
        )
    
    def test_referral_creation(self):
        """Test creating a referral"""
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PENDING
        )
        self.assertEqual(referral.referral_link, self.referral_link)
        self.assertEqual(referral.referred_user, self.referred)
        self.assertEqual(referral.status, Referral.Status.PENDING)
        self.assertIsNotNone(referral.signup_date)
    
    def test_mark_enrolled(self):
        """Test marking referral as enrolled"""
        from courses.models import Enrollment, Course
        
        # Create a course and enrollment for testing
        course = Course.objects.create(
            title='Test Course',
            description='Test',
            instructor=self.referrer,
            price=100
        )
        enrollment = Enrollment.objects.create(
            student=self.referred,
            course=course
        )
        
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PENDING
        )
        
        referral.mark_enrolled(enrollment)
        
        self.assertEqual(referral.status, Referral.Status.ENROLLED)
        self.assertEqual(referral.first_enrollment, enrollment)
        self.assertIsNotNone(referral.enrollment_date)
    
    def test_mark_paid(self):
        """Test marking referral as paid"""
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PAID
        )
        
        referral.mark_paid()
        
        self.assertEqual(referral.status, Referral.Status.PAID)
        self.assertIsNotNone(referral.payment_date)
    
    def test_is_successful(self):
        """Test is_successful method"""
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PAID  # Only PAID status is successful
        )
        
        self.assertTrue(referral.is_successful())
    
    def test_status_choices(self):
        """Test all status choices"""
        statuses = [
            Referral.Status.PENDING,
            Referral.Status.ENROLLED,
            Referral.Status.PAID,
            Referral.Status.REWARD_PENDING,
            Referral.Status.REWARD_CLAIMED
        ]
        
        for status in statuses:
            referral = Referral.objects.create(
                referral_link=self.referral_link,
                referred_user=User.objects.create_user(username=f'user_{status}'),
                status=status
            )
            self.assertEqual(referral.status, status)
    
    def test_unique_constraint(self):
        """Test unique constraint on referral_link + referred_user"""
        Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PENDING
        )
        
        # Try creating duplicate - should fail
        with self.assertRaises(Exception):
            Referral.objects.create(
                referral_link=self.referral_link,
                referred_user=self.referred,
                status=Referral.Status.PENDING
            )


class ReferralRewardTestCase(TestCase):
    """Test ReferralReward model"""
    
    def setUp(self):
        from courses.models import Enrollment, Course
        
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@test.com'
        )
        self.referred = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )
        self.referral_link = ReferralLink.objects.create(
            student=self.referrer,
            code=ReferralLink.generate_code(),
            referral_url='http://testserver/signup/?ref=TEST'
        )
        
        # Create course and enrollment
        self.course = Course.objects.create(
            title='Test Course',
            description='Test',
            instructor=self.referrer,
            price=100
        )
        self.enrollment = Enrollment.objects.create(
            student=self.referred,
            course=self.course
        )
        
        self.referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PAID,
            first_enrollment=self.enrollment
        )
    
    def test_reward_creation(self):
        """Test creating a reward"""
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=future_date
        )
        
        self.assertEqual(reward.referrer, self.referrer)
        self.assertEqual(reward.referral, self.referral)
        self.assertEqual(reward.status, ReferralReward.RewardStatus.AVAILABLE)
        self.assertIsNone(reward.claimed_at)
    
    def test_is_expired_not_expired(self):
        """Test is_expired check for valid rewards"""
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=future_date
        )
        
        self.assertFalse(reward.is_expired())
    
    def test_is_expired_expired(self):
        """Test is_expired check for expired rewards"""
        past_date = timezone.now() - timedelta(days=1)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=past_date
        )
        
        self.assertTrue(reward.is_expired())
    
    def test_can_claim_available(self):
        """Test can_claim for available, non-expired reward"""
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=future_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        self.assertTrue(reward.can_claim())
    
    def test_can_claim_expired(self):
        """Test can_claim for expired reward"""
        past_date = timezone.now() - timedelta(days=1)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=past_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        self.assertFalse(reward.can_claim())
    
    def test_can_claim_already_claimed(self):
        """Test can_claim for already claimed reward"""
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=future_date,
            status=ReferralReward.RewardStatus.CLAIMED
        )
        
        self.assertFalse(reward.can_claim())
    
    def test_claim_success(self):
        """Test claiming a reward successfully"""
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=future_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        result = reward.claim()
        
        self.assertTrue(result)
        self.assertEqual(reward.status, ReferralReward.RewardStatus.CLAIMED)
        self.assertIsNotNone(reward.claimed_at)
    
    def test_claim_failure_expired(self):
        """Test claiming an expired reward fails"""
        past_date = timezone.now() - timedelta(days=1)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=self.referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off coupon',
            expires_at=past_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        result = reward.claim()
        
        self.assertFalse(result)
        self.assertEqual(reward.status, ReferralReward.RewardStatus.AVAILABLE)
    
    def test_reward_types(self):
        """Test both reward types"""
        from courses.models import Enrollment, Course
        
        types = [
            ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            ReferralReward.RewardType.CREDIT_AMOUNT
        ]
        
        future_date = timezone.now() + timedelta(days=30)
        for i, reward_type in enumerate(types):
            course = Course.objects.create(
                title=f'Test Course {i}',
                description='Test',
                instructor=self.referrer,
                price=100
            )
            new_referred = User.objects.create_user(username=f'user_{reward_type}_{i}')
            enrollment = Enrollment.objects.create(
                student=new_referred,
                course=course
            )
            new_referral = Referral.objects.create(
                referral_link=self.referral_link,
                referred_user=new_referred,
                status=Referral.Status.PAID,
                first_enrollment=enrollment
            )
            
            reward = ReferralReward.objects.create(
                referrer=self.referrer,
                referral=new_referral,
                reward_type=reward_type,
                reward_value=Decimal('20.00'),
                reward_description=f'{reward_type} reward',
                expires_at=future_date
            )
            self.assertEqual(reward.reward_type, reward_type)


class ReferralFormsTestCase(TestCase):
    """Test referral forms"""
    
    def setUp(self):
        self.referrer = User.objects.create_user(
            username='referrer',
            email='referrer@test.com'
        )
        self.referred = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )
        self.referral_link = ReferralLink.objects.create(
            student=self.referrer,
            code=ReferralLink.generate_code()
        )
    
    def test_referral_reward_claim_form_valid(self):
        """Test valid reward claim form"""
        from .forms import ReferralRewardClaimForm
        
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred,
            status=Referral.Status.PAID
        )
        future_date = timezone.now() + timedelta(days=30)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off',
            expires_at=future_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        form = ReferralRewardClaimForm(
            data={'reward_id': reward.id},
            reward=reward
        )
        self.assertTrue(form.is_valid())
    
    def test_referral_reward_claim_form_expired_reward(self):
        """Test claim form with expired reward"""
        from .forms import ReferralRewardClaimForm
        
        referral = Referral.objects.create(
            referral_link=self.referral_link,
            referred_user=self.referred
        )
        past_date = timezone.now() - timedelta(days=1)
        reward = ReferralReward.objects.create(
            referrer=self.referrer,
            referral=referral,
            reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
            reward_value=Decimal('20.00'),
            reward_description='20% off',
            expires_at=past_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        
        form = ReferralRewardClaimForm(
            data={'reward_id': reward.id},
            reward=reward
        )
        self.assertFalse(form.is_valid())
    
    def test_referral_feedback_form_valid(self):
        """Test valid feedback form"""
        from .forms import ReferralFeedbackForm
        
        form = ReferralFeedbackForm(data={
            'rating': '5',
            'feedback': 'Great program!'
        })
        self.assertTrue(form.is_valid())
    
    def test_referral_feedback_form_feedback_too_long(self):
        """Test feedback form with text exceeding limit"""
        from .forms import ReferralFeedbackForm
        
        long_feedback = 'x' * 501  # Exceeds max 500 chars
        form = ReferralFeedbackForm(data={
            'rating': '5',
            'feedback': long_feedback
        })
        self.assertFalse(form.is_valid())


class ReferralViewsTestCase(TestCase):
    """Test referral views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.referred_user = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )
    
    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get('/referrals/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_api_generate_requires_login(self):
        """Test that API generate endpoint requires authentication"""
        response = self.client.post('/referrals/api/generate/')
        self.assertEqual(response.status_code, 302)
    
    def test_api_stats_requires_login(self):
        """Test that API stats endpoint requires authentication"""
        response = self.client.get('/referrals/api/stats/')
        self.assertEqual(response.status_code, 302)


class ReferralIntegrationTestCase(TestCase):
    """Test complete referral flow"""
    
    def test_complete_referral_flow(self):
        """Test complete referral lifecycle"""
        from courses.models import Enrollment, Course
        
        # Create referrer
        referrer = User.objects.create_user(
            username='referrer',
            email='referrer@test.com'
        )
        
        # Create referred user
        referred = User.objects.create_user(
            username='referred',
            email='referred@test.com'
        )
        
        # Create referral link
        link = ReferralLink.objects.create(
            student=referrer,
            code=ReferralLink.generate_code(),
            referral_url='http://testserver/signup/?ref=TEST'
        )
        self.assertIsNotNone(link.code)
        
        # Create referral (signup)
        referral = Referral.objects.create(
            referral_link=link,
            referred_user=referred,
            status=Referral.Status.PENDING
        )
        self.assertEqual(referral.status, Referral.Status.PENDING)
        self.assertFalse(referral.is_successful())
        
        # Create course and enrollment
        course = Course.objects.create(
            title='Test Course',
            description='Test',
            instructor=referrer,
            price=100
        )
        enrollment = Enrollment.objects.create(
            student=referred,
            course=course
        )
        
        # Mark as enrolled
        referral.mark_enrolled(enrollment)
        self.assertEqual(referral.status, Referral.Status.ENROLLED)
        
        # Mark as paid
        referral.mark_paid()
        self.assertEqual(referral.status, Referral.Status.PAID)
        self.assertTrue(referral.is_successful())
        
        # Create reward
        settings = ReferralSettings.get_settings()
        future_date = timezone.now() + timedelta(days=settings.reward_validity_days)
        reward = ReferralReward.objects.create(
            referrer=referrer,
            referral=referral,
            reward_type=settings.reward_type,
            reward_value=Decimal('10.00'),
            reward_description='10% referral discount',
            expires_at=future_date,
            status=ReferralReward.RewardStatus.AVAILABLE
        )
        self.assertEqual(reward.status, ReferralReward.RewardStatus.AVAILABLE)
        self.assertFalse(reward.is_expired())
        self.assertTrue(reward.can_claim())
        
        # Claim reward
        success = reward.claim()
        self.assertTrue(success)
        self.assertEqual(reward.status, ReferralReward.RewardStatus.CLAIMED)
        self.assertIsNotNone(reward.claimed_at)
