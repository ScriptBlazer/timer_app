from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from customers.models import Customer
from .models import Project


class ProjectModelTest(TestCase):
    """Test Project model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.customer = Customer.objects.create(name='Test Customer', user=self.user)
    
    def test_project_creation(self):
        """Test creating a project"""
        project = Project.objects.create(
            name='Test Project',
            customer=self.customer,
            status='active'
        )
        self.assertEqual(str(project), 'Test Project (Test Customer)')
        self.assertEqual(project.customer, self.customer)
        self.assertEqual(project.status, 'active')
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)
    
    def test_project_default_status(self):
        """Test project defaults to active status"""
        project = Project.objects.create(
            name='Test Project',
            customer=self.customer
        )
        self.assertEqual(project.status, 'active')
    
    def test_project_status_choices(self):
        """Test project status choices"""
        project = Project.objects.create(
            name='Test Project',
            customer=self.customer,
            status='completed'
        )
        self.assertEqual(project.status, 'completed')
        self.assertEqual(project.get_status_display(), 'Completed')
    
    def test_project_ordering(self):
        """Test project ordering by created_at descending"""
        project1 = Project.objects.create(name='First Project', customer=self.customer)
        project2 = Project.objects.create(name='Second Project', customer=self.customer)
        projects = Project.objects.all()
        self.assertEqual(projects[0].name, 'Second Project')
        self.assertEqual(projects[1].name, 'First Project')
    
    def test_project_total_duration_empty(self):
        """Test project total duration with no timers"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        self.assertEqual(project.total_duration_seconds(), 0)
    
    def test_project_total_cost_empty(self):
        """Test project total cost with no timers"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        self.assertEqual(project.total_cost(), 0)
    
    def test_project_total_duration_with_timers(self):
        """Test project total duration calculation with timers"""
        from timer.models import Timer, ProjectTimer, TimerSession
        from django.utils import timezone
        from datetime import timedelta
        
        project = Project.objects.create(name='Test Project', customer=self.customer)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=project, timer=timer)
        
        # Create a session
        start_time = timezone.now() - timedelta(hours=3)
        end_time = timezone.now()
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertAlmostEqual(project.total_duration_seconds(), 10800, delta=1)
    
    def test_project_total_cost_with_timers(self):
        """Test project total cost calculation with timers"""
        from timer.models import Timer, ProjectTimer, TimerSession
        from django.utils import timezone
        from datetime import timedelta
        
        project = Project.objects.create(name='Test Project', customer=self.customer)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=project, timer=timer)
        
        # Create a session
        start_time = timezone.now() - timedelta(hours=3)
        end_time = timezone.now()
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        
        self.assertEqual(project.total_cost(), 300.00)


class ProjectViewTest(TestCase):
    """Test Project views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.customer = Customer.objects.create(name='Test Customer', user=self.user)
    
    def test_project_list_requires_login(self):
        """Test project list requires authentication"""
        response = self.client.get('/projects/')
        self.assertRedirects(response, '/login/?next=/projects/')
    
    def test_project_list_accessible_when_logged_in(self):
        """Test project list is accessible when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/projects/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projects')
    
    def test_project_list_shows_projects(self):
        """Test project list displays projects"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get('/projects/')
        self.assertContains(response, 'Test Project')
    
    def test_project_add_requires_login(self):
        """Test project add requires authentication"""
        response = self.client.get('/projects/add/?customer=1')
        # The redirect includes the query parameter in the next URL
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/login/?next='))
    
    def test_project_add_get(self):
        """Test project add form display"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/projects/add/?customer={self.customer.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Project')
    
    def test_project_add_post(self):
        """Test creating a project via form"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(f'/projects/add/?customer={self.customer.pk}', {
            'name': 'New Project'
        })
        # After creation, redirects to project detail page
        project = Project.objects.get(name='New Project')
        self.assertRedirects(response, f'/projects/{project.pk}/')
        self.assertTrue(Project.objects.filter(name='New Project').exists())
    
    def test_project_detail_requires_login(self):
        """Test project detail requires authentication"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/')
        self.assertRedirects(response, f'/login/?next=/projects/{project.pk}/')
    
    def test_project_detail_accessible(self):
        """Test viewing project detail"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
    
    def test_project_edit_requires_login(self):
        """Test project edit requires authentication"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/edit/')
        self.assertRedirects(response, f'/login/?next=/projects/{project.pk}/edit/')
    
    def test_project_edit_get(self):
        """Test project edit form display"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/edit/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Project')
    
    def test_project_edit_post(self):
        """Test editing a project"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Old Name', customer=self.customer)
        response = self.client.post(f'/projects/{project.pk}/edit/', {
            'name': 'New Name'
        })
        self.assertRedirects(response, f'/projects/{project.pk}/')
        project.refresh_from_db()
        self.assertEqual(project.name, 'New Name')
    
    def test_project_delete_requires_login(self):
        """Test project delete requires authentication"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/delete/')
        self.assertRedirects(response, f'/login/?next=/projects/{project.pk}/delete/')
    
    def test_project_delete_get(self):
        """Test project delete confirmation page"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/delete/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
    
    def test_project_delete_post(self):
        """Test deleting a project"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.post(f'/projects/{project.pk}/delete/')
        self.assertRedirects(response, f'/customers/{self.customer.pk}/')
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())
    
    def test_project_complete_requires_login(self):
        """Test project complete requires authentication"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/complete/')
        self.assertRedirects(response, f'/login/?next=/projects/{project.pk}/complete/')
    
    def test_project_complete_get(self):
        """Test project complete confirmation page"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.get(f'/projects/{project.pk}/complete/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Project')
    
    def test_project_complete_post(self):
        """Test marking a project as completed"""
        self.client.login(username='testuser', password='testpass123')
        project = Project.objects.create(name='Test Project', customer=self.customer)
        response = self.client.post(f'/projects/{project.pk}/complete/')
        self.assertRedirects(response, f'/projects/{project.pk}/')
        project.refresh_from_db()
        self.assertEqual(project.status, 'completed')
    
    def test_project_workspace_isolation(self):
        """Test projects are isolated by workspace"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        project = Project.objects.create(name='Other Project', customer=other_customer)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/projects/{project.pk}/')
        # Should redirect to customer_list when permission denied (not 404)
        self.assertRedirects(response, '/customers/')
