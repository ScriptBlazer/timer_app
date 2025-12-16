from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Customer


class CustomerModelTest(TestCase):
    """Test Customer model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_customer_creation(self):
        """Test creating a customer"""
        customer = Customer.objects.create(
            name='Test Customer',
            user=self.user
        )
        self.assertEqual(str(customer), 'Test Customer')
        self.assertEqual(customer.user, self.user)
        self.assertIsNotNone(customer.created_at)
        self.assertIsNotNone(customer.updated_at)
    
    def test_customer_ordering(self):
        """Test customer ordering by name"""
        Customer.objects.create(name='Zebra Customer', user=self.user)
        Customer.objects.create(name='Alpha Customer', user=self.user)
        customers = Customer.objects.all()
        self.assertEqual(customers[0].name, 'Alpha Customer')
        self.assertEqual(customers[1].name, 'Zebra Customer')
    
    def test_customer_total_duration_empty(self):
        """Test customer total duration with no projects"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.assertEqual(customer.total_duration_seconds(), 0)
    
    def test_customer_total_cost_empty(self):
        """Test customer total cost with no projects"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.assertEqual(customer.total_cost(), 0)
    
    def test_customer_total_duration_with_projects(self):
        """Test customer total duration calculation with projects"""
        from projects.models import Project
        from timer.models import Timer, ProjectTimer, TimerSession
        from django.utils import timezone
        from datetime import timedelta
        
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        project = Project.objects.create(name='Test Project', customer=customer)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=project, timer=timer)
        
        # Create a session
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now()
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertAlmostEqual(customer.total_duration_seconds(), 7200, delta=1)
    
    def test_customer_total_cost_with_projects(self):
        """Test customer total cost calculation with projects"""
        from projects.models import Project
        from timer.models import Timer, ProjectTimer, TimerSession
        from django.utils import timezone
        from datetime import timedelta
        
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        project = Project.objects.create(name='Test Project', customer=customer)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=project, timer=timer)
        
        # Create a session
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now()
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertEqual(customer.total_cost(), 200.00)


class CustomerViewTest(TestCase):
    """Test Customer views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_customer_list_requires_login(self):
        """Test customer list requires authentication"""
        response = self.client.get('/customers/')
        self.assertRedirects(response, '/login/?next=/customers/')
    
    def test_customer_list_accessible_when_logged_in(self):
        """Test customer list is accessible when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/customers/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customers')
    
    def test_customer_list_shows_customers(self):
        """Test customer list displays customers"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get('/customers/')
        self.assertContains(response, 'Test Customer')
    
    def test_customer_add_requires_login(self):
        """Test customer add requires authentication"""
        response = self.client.get('/customers/add/')
        self.assertRedirects(response, '/login/?next=/customers/add/')
    
    def test_customer_add_get(self):
        """Test customer add form display"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/customers/add/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Customer')
    
    def test_customer_add_post(self):
        """Test creating a customer via form"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post('/customers/add/', {
            'name': 'New Customer'
        })
        # After creation, redirects to customer detail page
        customer = Customer.objects.get(name='New Customer')
        self.assertRedirects(response, f'/customers/{customer.pk}/')
        self.assertTrue(Customer.objects.filter(name='New Customer').exists())
    
    def test_customer_detail_requires_login(self):
        """Test customer detail requires authentication"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/')
        self.assertRedirects(response, f'/login/?next=/customers/{customer.pk}/')
    
    def test_customer_detail_accessible(self):
        """Test viewing customer detail"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')
    
    def test_customer_edit_requires_login(self):
        """Test customer edit requires authentication"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/edit/')
        self.assertRedirects(response, f'/login/?next=/customers/{customer.pk}/edit/')
    
    def test_customer_edit_get(self):
        """Test customer edit form display"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Customer')
    
    def test_customer_edit_post(self):
        """Test editing a customer"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Old Name', user=self.user)
        response = self.client.post(f'/customers/{customer.pk}/edit/', {
            'name': 'New Name'
        })
        self.assertRedirects(response, f'/customers/{customer.pk}/')
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'New Name')
    
    def test_customer_delete_requires_login(self):
        """Test customer delete requires authentication"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/delete/')
        self.assertRedirects(response, f'/login/?next=/customers/{customer.pk}/delete/')
    
    def test_customer_delete_get(self):
        """Test customer delete confirmation page"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')
    
    def test_customer_delete_post(self):
        """Test deleting a customer"""
        self.client.login(username='testuser', password='testpass123')
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.post(f'/customers/{customer.pk}/delete/')
        self.assertRedirects(response, '/customers/')
        self.assertFalse(Customer.objects.filter(pk=customer.pk).exists())
    
    def test_customer_workspace_isolation(self):
        """Test customers are isolated by workspace"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        customer = Customer.objects.create(name='Other Customer', user=other_user)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/customers/{customer.pk}/')
        # Should not be able to access other user's customer
        self.assertEqual(response.status_code, 404)
