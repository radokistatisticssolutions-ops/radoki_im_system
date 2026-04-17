from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Course, Enrollment, Resource
from .forms import CourseForm, ResourceForm
from core.models import AdminAccessControl

User = get_user_model()


def login_normal(client, username, password):
    """Login via test client and set normal site auth session flag."""
    assert client.login(username=username, password=password)
    session = client.session
    session['_normal_site_auth'] = True
    session.save()


class CourseModelTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )

    def test_course_creation_with_new_fields(self):
        """Test creating a course with all new fields"""
        course = Course.objects.create(
            instructor=self.instructor,
            title='Test Course',
            description='Test Description',
            price=50000.00,  # TZS
            duration='3 months',
            mode='HYBRID',
            curriculum='Detailed curriculum content...',
            total_hours=120
        )
        self.assertEqual(course.price, 50000.00)
        self.assertEqual(course.duration, '3 months')
        self.assertEqual(course.mode, 'HYBRID')
        self.assertEqual(course.get_mode_display(), 'Hybrid (Online & Offline)')
        self.assertEqual(course.curriculum, 'Detailed curriculum content...')
        self.assertEqual(course.total_hours, 120)
        self.assertEqual(str(course), 'Test Course')

    def test_course_default_values(self):
        """Test default values for new fields"""
        course = Course.objects.create(
            instructor=self.instructor,
            title='Default Course',
            description='Default Description'
        )
        self.assertEqual(course.price, 0.00)
        self.assertEqual(course.duration, 'TBD')
        self.assertEqual(course.mode, 'ONLINE')
        self.assertEqual(course.curriculum, 'Curriculum to be updated.')
        self.assertEqual(course.total_hours, 0)


class CourseFormTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )

    def test_course_form_valid_data(self):
        """Test CourseForm with valid data including new fields"""
        form_data = {
            'title': 'Form Test Course',
            'description': 'Form test description',
            'price': '75000.00',
            'duration': '6 months',
            'mode': 'OFFLINE',
            'total_hours': '200',
            'curriculum': 'Comprehensive curriculum details...'
        }
        form = CourseForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_course_form_invalid_price(self):
        """Test CourseForm with invalid price"""
        form_data = {
            'title': 'Invalid Price Course',
            'description': 'Test description',
            'price': '-100.00',  # Invalid negative price
            'duration': '3 months',
            'mode': 'ONLINE',
            'total_hours': '100',
            'curriculum': 'Curriculum'
        }
        form = CourseForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_course_form_invalid_total_hours(self):
        """Test CourseForm with invalid total_hours"""
        form_data = {
            'title': 'Invalid Hours Course',
            'description': 'Test description',
            'price': '50000.00',
            'duration': '3 months',
            'mode': 'ONLINE',
            'total_hours': '-10',  # Invalid negative hours
            'curriculum': 'Curriculum'
        }
        form = CourseForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_hours', form.errors)


class CourseViewTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            title='View Test Course',
            description='Test course for views',
            price=100000.00,
            duration='4 months',
            mode='HYBRID',
            curriculum='Test curriculum content',
            total_hours=150
        )

    def test_course_list_view(self):
        """Test course list view displays courses"""
        login_normal(self.client, username='student', password='testpass123')
        response = self.client.get(reverse('courses:course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, '100000')  # Price
        self.assertContains(response, 'Hybrid')  # Mode display

    def test_course_detail_view(self):
        """Test course detail view displays all new fields"""
        login_normal(self.client, username='student', password='testpass123')
        response = self.client.get(reverse('courses:course_detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, '100000')  # Price
        self.assertContains(response, '4 months')  # Duration
        self.assertContains(response, 'Hybrid (Online & Offline)')  # Mode
        self.assertContains(response, '150 Hours')  # Total hours
        self.assertContains(response, 'Test curriculum content')  # Curriculum

    def test_create_course_view(self):
        """Test course creation with new fields"""
        login_normal(self.client, username='instructor', password='testpass123')
        course_data = {
            'title': 'Created Course',
            'description': 'Created description',
            'price': '200000.00',
            'duration': '12 months',
            'mode': 'OFFLINE',
            'total_hours': '300',
            'curriculum': 'Created curriculum'
        }
        response = self.client.post(reverse('courses:create_course'), course_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        created_course = Course.objects.get(title='Created Course')
        self.assertEqual(created_course.price, 200000.00)
        self.assertEqual(created_course.mode, 'OFFLINE')

    def test_staff_gets_admin_403_for_resource_preview(self):
        # Staff user (admin context) should see 403 instead of user-side redirect
        staff_user = User.objects.create_user(
            username='staff',
            email='staff@test.com',
            password='testpass123',
            is_staff=True,
            role='student'  # role may be student but is_staff indicates admin U/I
        )
        resource_file = SimpleUploadedFile('test.txt', b'Some content')
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource',
            file=resource_file,
            download_allowed=False
        )

        self.assertTrue(self.client.login(username='staff', password='testpass123'))
        session = self.client.session
        session['_normal_site_auth'] = True
        session.save()
        self.assertIn('_auth_user_id', self.client.session)
        self.assertIn('_auth_user_backend', self.client.session)
        # verify login succeeded and session persists
        response = self.client.get(reverse('courses:course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('courses:preview_resource', kwargs={'resource_id': resource.id}))

        self.assertEqual(response.status_code, 403, f'Expected 403 but got {response.status_code} (redirect: {getattr(response, "url", response)})')
        self.assertContains(response, 'Access denied', status_code=403)

    def test_staff_with_resource_view_permission_can_preview_resource(self):
        staff_user = User.objects.create_user(
            username='staff_view',
            email='staff_view@test.com',
            password='testpass123',
            is_staff=True,
            role='student'
        )
        AdminAccessControl.objects.create(
            admin_user=staff_user,
            model='resource',
            permission='view',
            granted_by=self.instructor
        )

        resource_file = SimpleUploadedFile('testview.txt', b'Preview content')
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource View',
            file=resource_file,
            download_allowed=False
        )

        login_normal(self.client, username='staff_view', password='testpass123')
        response = self.client.get(reverse('courses:preview_resource', kwargs={'resource_id': resource.id}))

        self.assertEqual(response.status_code, 200)

    def test_staff_with_view_permission_cannot_download_resource(self):
        staff_user = User.objects.create_user(
            username='staff_view_download',
            email='staff_view_download@test.com',
            password='testpass123',
            is_staff=True,
            role='student'
        )
        AdminAccessControl.objects.create(
            admin_user=staff_user,
            model='resource',
            permission='view',
            granted_by=self.instructor
        )

        resource_file = SimpleUploadedFile('testview2.txt', b'Download attempt')
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource View2',
            file=resource_file,
            download_allowed=False
        )

        login_normal(self.client, username='staff_view_download', password='testpass123')
        response = self.client.get(reverse('courses:download_resource', kwargs={'resource_id': resource.id}))

        self.assertEqual(response.status_code, 403)

    def test_staff_with_resource_export_permission_can_download_resource(self):
        staff_user = User.objects.create_user(
            username='staff_export',
            email='staff_export@test.com',
            password='testpass123',
            is_staff=True,
            role='student'
        )
        AdminAccessControl.objects.create(
            admin_user=staff_user,
            model='resource',
            permission='export',
            granted_by=self.instructor
        )

        resource_file = SimpleUploadedFile('testexport.txt', b'Download content')
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource Export',
            file=resource_file,
            download_allowed=False
        )

        login_normal(self.client, username='staff_export', password='testpass123')
        response = self.client.get(reverse('courses:download_resource', kwargs={'resource_id': resource.id}))

        self.assertEqual(response.status_code, 200)

    def test_staff_gets_admin_403_for_resource_download(self):
        staff_user = User.objects.create_user(
            username='staff2',
            email='staff2@test.com',
            password='testpass123',
            is_staff=True,
            role='student'
        )
        resource_file = SimpleUploadedFile('test-download.txt', b'PDF? no')
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource Download',
            file=resource_file,
            download_allowed=False
        )

        login_normal(self.client, username='staff2', password='testpass123')
        response = self.client.get(reverse('courses:download_resource', kwargs={'resource_id': resource.id}))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Access denied', status_code=403)


class AdminAccessControlUITest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        self.staff = User.objects.create_user(
            username='staff_acl',
            email='staff_acl@test.com',
            password='testpass123',
            is_staff=True,
            role='student'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            title='ACL Course',
            description='ACL course for admin tests',
            price=90000.00,
            duration='6 months',
            mode='ONLINE',
            curriculum='ACL curriculum',
            total_hours=120
        )

    def test_admin_dashboard_shows_only_allowed_models(self):
        AdminAccessControl.objects.create(
            admin_user=self.staff,
            model='resource',
            permission='view',
            granted_by=self.instructor
        )

        self.assertTrue(self.client.login(username='staff_acl', password='testpass123'))
        session = self.client.session
        session['_normal_site_auth'] = True
        session.save()

        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        app_list = response.context.get('app_list', [])
        self.assertTrue(app_list, "App list context should be provided")

        # Resource is allowed by ACL and should be visible
        resource_seen = any(
            model.get('object_name', '').lower() == 'resource'
            for app in app_list
            for model in app.get('models', [])
        )
        self.assertTrue(resource_seen, "Resource model should be in app list")

        # Course is not allowed for this user and should be omitted
        course_seen = any(
            model.get('object_name', '').lower() == 'course'
            for app in app_list
            for model in app.get('models', [])
        )
        self.assertFalse(course_seen, "Course model should not be in app list")

    def test_payment_acl_models_resolve_to_paymentmethod(self):
        AdminAccessControl.objects.create(
            admin_user=self.staff,
            model='payment',
            permission='view',
            granted_by=self.instructor
        )

        self.assertTrue(self.client.login(username='staff_acl', password='testpass123'))
        session = self.client.session
        session['_normal_site_auth'] = True
        session.save()

        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

        app_list = response.context.get('app_list', [])
        self.assertTrue(app_list, "App list context should be provided")

        paymentmethod_seen = any(
            model.get('object_name', '').lower() == 'paymentmethod'
            for app in app_list
            for model in app.get('models', [])
        )
        self.assertTrue(paymentmethod_seen, "PaymentMethod admin model should be visible when payment ACL is granted")


class EnrollmentTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            title='Enrollment Test Course',
            description='Test course for enrollment',
            price=50000.00,
            duration='2 months',
            mode='ONLINE',
            curriculum='Enrollment test curriculum',
            total_hours=80
        )

    def test_enrollment_creation(self):
        """Test student can enroll in course"""
        login_normal(self.client, username='student', password='testpass123')
        response = self.client.get(reverse('courses:enroll_course', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 302)  # Redirect
        enrollment = Enrollment.objects.get(student=self.student, course=self.course)
        self.assertFalse(enrollment.approved)  # Should be pending approval


class PaymentMethodTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            title='Payment Method Test Course',
            description='Test course for payment methods',
            price=50000.00,
            duration='2 months',
            mode='ONLINE',
            curriculum='Payment method test curriculum',
            total_hours=60
        )

    def test_payment_method_creation(self):
        """Test payment method can be created for course"""
        payment_method = PaymentMethod.objects.create(
            course=self.course,
            method_type='MPESA',
            lipa_namba='255712345678',
            merchant_id='MERCHANT123',
            merchant_name='Test Merchant Ltd'
        )
        self.assertEqual(str(payment_method), 'M-Pesa - Payment Method Test Course')
        self.assertEqual(payment_method.get_method_type_display(), 'M-Pesa')
        self.assertEqual(self.course.payment_methods.count(), 1)

    def test_unique_payment_method_per_course(self):
        """Test that only one payment method of each type per course is allowed"""
        PaymentMethod.objects.create(
            course=self.course,
            method_type='MPESA',
            lipa_namba='255712345678',
            merchant_id='MERCHANT123',
            merchant_name='Test Merchant Ltd'
        )
        # This should raise an IntegrityError
        with self.assertRaises(Exception):
            PaymentMethod.objects.create(
                course=self.course,
                method_type='MPESA',  # Same type for same course
                lipa_namba='255798765432',
                merchant_id='MERCHANT456',
                merchant_name='Another Merchant'
            )

    def test_multiple_payment_methods_different_types(self):
        """Test that different payment method types are allowed for same course"""
        mpesa = PaymentMethod.objects.create(
            course=self.course,
            method_type='MPESA',
            lipa_namba='255712345678',
            merchant_id='MERCHANT123',
            merchant_name='M-Pesa Merchant'
        )
        airtel = PaymentMethod.objects.create(
            course=self.course,
            method_type='AIRTEL',
            lipa_namba='255787654321',
            merchant_id='AIRTEL456',
            merchant_name='Airtel Merchant'
        )
        self.assertEqual(self.course.payment_methods.count(), 2)
        self.assertEqual(mpesa.get_method_type_display(), 'M-Pesa')
        self.assertEqual(airtel.get_method_type_display(), 'Airtel Money')


class ResourceTest(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            title='Resource Test Course',
            description='Test course for resources',
            price=30000.00,
            duration='1 month',
            mode='ONLINE',
            curriculum='Resource test curriculum',
            total_hours=40
        )

    def test_resource_creation(self):
        """Test resource can be created for course"""
        from django.core.files.base import ContentFile
        resource = Resource.objects.create(
            course=self.course,
            title='Test Resource',
            file=ContentFile('test content', name='test.pdf')
        )
        self.assertEqual(str(resource), 'Test Resource (Resource Test Course)')
        self.assertEqual(self.course.resources.count(), 1)
