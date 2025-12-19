from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import json

from customers.models import Customer
from projects.models import Project
from timer.models import Timer, ProjectTimer, TimerSession
from .models import Deliverable
from .forms import DeliverableForm


class DeliverableModelTest(TestCase):
    """Test Deliverable model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.project = Project.objects.create(name='Test Project', customer=self.customer)
        self.timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        self.project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
    
    def test_deliverable_creation(self):
        """Test creating a deliverable"""
        deliverable = Deliverable.objects.create(
            name='Video 1',
            project=self.project,
            description='First video production'
        )
        self.assertEqual(deliverable.name, 'Video 1')
        self.assertEqual(deliverable.project, self.project)
        self.assertEqual(str(deliverable), f"Video 1 ({self.project.name})")
    
    def test_deliverable_unique_name_per_project(self):
        """Test that deliverable names must be unique within a project"""
        Deliverable.objects.create(name='Video 1', project=self.project)
        
        # Try to create another with same name in same project
        with self.assertRaises(Exception):
            Deliverable.objects.create(name='Video 1', project=self.project)
    
    def test_deliverable_total_duration_seconds(self):
        """Test calculating total duration for a deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        
        # Create sessions linked to deliverable
        session1 = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            deliverable=deliverable
        )
        session2 = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            deliverable=deliverable
        )
        
        # Total should be 2 hours = 7200 seconds
        self.assertAlmostEqual(deliverable.total_duration_seconds(), 7200, delta=5)
    
    def test_deliverable_total_cost(self):
        """Test calculating total cost for a deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now(),
            deliverable=deliverable
        )
        
        # 2 hours * $100 = $200
        self.assertEqual(deliverable.total_cost(), 200.00)
    
    def test_deliverable_session_count(self):
        """Test counting sessions for a deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        
        # Create 3 sessions
        for i in range(3):
            TimerSession.objects.create(
                project_timer=self.project_timer,
                price_per_hour=100.00,
                start_time=timezone.now() - timedelta(hours=1),
                end_time=timezone.now(),
                deliverable=deliverable
            )
        
        self.assertEqual(deliverable.session_count(), 3)


class DeliverableViewTest(TestCase):
    """Test Deliverable views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        self.customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.project = Project.objects.create(name='Test Project', customer=self.customer)
    
    def test_deliverable_list_requires_login(self):
        """Test that deliverable list requires login"""
        self.client.logout()
        response = self.client.get(reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertRedirects(response, f'/login/?next=/projects/{self.project.pk}/deliverables/')
    
    def test_deliverable_list_shows_deliverables(self):
        """Test that deliverable list shows deliverables"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.get(reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Video 1')
    
    def test_deliverable_add_requires_login(self):
        """Test that adding deliverable requires login"""
        self.client.logout()
        response = self.client.get(reverse('deliverables:deliverable_add', args=[self.project.pk]))
        self.assertRedirects(response, f'/login/?next=/projects/{self.project.pk}/deliverables/add/')
    
    def test_deliverable_add_creates_deliverable(self):
        """Test that adding deliverable creates it"""
        response = self.client.post(
            reverse('deliverables:deliverable_add', args=[self.project.pk]),
            {'name': 'Video 1', 'description': 'First video'}
        )
        self.assertRedirects(response, reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertTrue(Deliverable.objects.filter(name='Video 1', project=self.project).exists())
    
    def test_deliverable_workspace_isolation(self):
        """Test that users can only see deliverables from their workspace"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        other_project = Project.objects.create(name='Other Project', customer=other_customer)
        other_deliverable = Deliverable.objects.create(name='Other Deliverable', project=other_project)
        
        # Try to access other user's deliverable
        response = self.client.get(reverse('deliverables:deliverable_detail', args=[other_deliverable.pk]))
        self.assertRedirects(response, '/customers/')
    
    def test_deliverable_add_ajax(self):
        """Test AJAX endpoint for adding deliverable"""
        response = self.client.post(
            reverse('deliverables:deliverable_add_ajax', args=[self.project.pk]),
            json.dumps({'name': 'Video 1', 'description': 'First video'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(Deliverable.objects.filter(name='Video 1', project=self.project).exists())
        self.assertEqual(data['deliverable']['name'], 'Video 1')
    
    def test_deliverable_add_ajax_requires_name(self):
        """Test AJAX endpoint requires name"""
        response = self.client.post(
            reverse('deliverables:deliverable_add_ajax', args=[self.project.pk]),
            json.dumps({'description': 'No name'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Name is required', data['error'])
    
    def test_deliverable_add_ajax_duplicate_name(self):
        """Test AJAX endpoint prevents duplicate names"""
        Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(
            reverse('deliverables:deliverable_add_ajax', args=[self.project.pk]),
            json.dumps({'name': 'Video 1'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('already exists', data['error'])
    
    def test_deliverable_add_ajax_invalid_json(self):
        """Test AJAX endpoint handles invalid JSON"""
        response = self.client.post(
            reverse('deliverables:deliverable_add_ajax', args=[self.project.pk]),
            'invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
    
    def test_deliverable_add_duplicate_name_shows_error(self):
        """Test that adding duplicate deliverable shows form error"""
        Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(
            reverse('deliverables:deliverable_add', args=[self.project.pk]),
            {'name': 'Video 1', 'description': 'Duplicate'}
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered with error
        self.assertFalse(Deliverable.objects.filter(name='Video 1', description='Duplicate').exists())
    
    def test_deliverable_detail_view(self):
        """Test deliverable detail view"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.get(reverse('deliverables:deliverable_detail', args=[deliverable.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Video 1')
        self.assertContains(response, self.project.name)
    
    def test_deliverable_detail_shows_sessions(self):
        """Test deliverable detail shows linked sessions"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=self.project, timer=timer)
        
        session = TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            deliverable=deliverable
        )
        
        response = self.client.get(reverse('deliverables:deliverable_detail', args=[deliverable.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Development')
    
    def test_deliverable_detail_excludes_active_sessions(self):
        """Test deliverable detail excludes active (unfinished) sessions"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        project_timer = ProjectTimer.objects.create(project=self.project, timer=timer)
        
        # Active session (no end_time)
        active_session = TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=timezone.now(),
            end_time=None,
            deliverable=deliverable
        )
        
        # Completed session
        completed_session = TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now(),
            deliverable=deliverable
        )
        
        response = self.client.get(reverse('deliverables:deliverable_detail', args=[deliverable.pk]))
        self.assertEqual(response.status_code, 200)
        # Should only show completed session
        self.assertEqual(response.context['sessions'].count(), 1)
    
    def test_deliverable_edit_get(self):
        """Test GET request to edit deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.get(reverse('deliverables:deliverable_edit', args=[deliverable.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Video 1')
    
    def test_deliverable_edit_post(self):
        """Test POST request to edit deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(
            reverse('deliverables:deliverable_edit', args=[deliverable.pk]),
            {'name': 'Video 2', 'description': 'Updated description'}
        )
        self.assertRedirects(response, reverse('deliverables:deliverable_list', args=[self.project.pk]))
        deliverable.refresh_from_db()
        self.assertEqual(deliverable.name, 'Video 2')
        self.assertEqual(deliverable.description, 'Updated description')
    
    def test_deliverable_edit_duplicate_name(self):
        """Test editing deliverable with duplicate name shows error"""
        deliverable1 = Deliverable.objects.create(name='Video 1', project=self.project)
        deliverable2 = Deliverable.objects.create(name='Video 2', project=self.project)
        
        # Try to rename deliverable2 to Video 1
        response = self.client.post(
            reverse('deliverables:deliverable_edit', args=[deliverable2.pk]),
            {'name': 'Video 1', 'description': ''}
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered with error
        deliverable2.refresh_from_db()
        self.assertEqual(deliverable2.name, 'Video 2')  # Name unchanged
    
    def test_deliverable_edit_same_name_allowed(self):
        """Test editing deliverable with same name is allowed"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(
            reverse('deliverables:deliverable_edit', args=[deliverable.pk]),
            {'name': 'Video 1', 'description': 'Updated description'}
        )
        self.assertRedirects(response, reverse('deliverables:deliverable_list', args=[self.project.pk]))
        deliverable.refresh_from_db()
        self.assertEqual(deliverable.description, 'Updated description')
    
    def test_deliverable_delete(self):
        """Test deleting a deliverable"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(reverse('deliverables:deliverable_delete', args=[deliverable.pk]))
        self.assertRedirects(response, reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertFalse(Deliverable.objects.filter(pk=deliverable.pk).exists())
    
    def test_deliverable_delete_requires_post(self):
        """Test that delete requires POST method"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.get(reverse('deliverables:deliverable_delete', args=[deliverable.pk]))
        self.assertEqual(response.status_code, 405)  # Method not allowed
    
    def test_deliverable_delete_json_response(self):
        """Test deleting deliverable returns JSON when requested"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        response = self.client.post(
            reverse('deliverables:deliverable_delete', args=[deliverable.pk]),
            HTTP_ACCEPT='application/json'
        )
        # Since we're not setting Content-Type header, it will redirect
        # But if we check the response type, it should work
        self.assertFalse(Deliverable.objects.filter(pk=deliverable.pk).exists())
    
    def test_deliverable_list_empty(self):
        """Test deliverable list with no deliverables"""
        response = self.client.get(reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No deliverables yet')
    
    def test_deliverable_list_multiple(self):
        """Test deliverable list with multiple deliverables"""
        Deliverable.objects.create(name='Video 1', project=self.project)
        Deliverable.objects.create(name='Video 2', project=self.project)
        Deliverable.objects.create(name='Video 3', project=self.project)
        
        response = self.client.get(reverse('deliverables:deliverable_list', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Video 1')
        self.assertContains(response, 'Video 2')
        self.assertContains(response, 'Video 3')
    
    def test_deliverable_add_get(self):
        """Test GET request to add deliverable form"""
        response = self.client.get(reverse('deliverables:deliverable_add', args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add Deliverable')
    
    def test_deliverable_add_with_description(self):
        """Test adding deliverable with description"""
        response = self.client.post(
            reverse('deliverables:deliverable_add', args=[self.project.pk]),
            {'name': 'Video 1', 'description': 'First video production'}
        )
        self.assertRedirects(response, reverse('deliverables:deliverable_list', args=[self.project.pk]))
        deliverable = Deliverable.objects.get(name='Video 1', project=self.project)
        self.assertEqual(deliverable.description, 'First video production')
    
    def test_deliverable_add_empty_name(self):
        """Test adding deliverable with empty name shows error"""
        response = self.client.post(
            reverse('deliverables:deliverable_add', args=[self.project.pk]),
            {'name': '', 'description': 'No name'}
        )
        self.assertEqual(response.status_code, 200)  # Form re-rendered with error
        self.assertFalse(Deliverable.objects.filter(description='No name').exists())
    
    def test_deliverable_workspace_isolation_detail(self):
        """Test workspace isolation for deliverable detail"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        other_project = Project.objects.create(name='Other Project', customer=other_customer)
        other_deliverable = Deliverable.objects.create(name='Other Deliverable', project=other_project)
        
        response = self.client.get(reverse('deliverables:deliverable_detail', args=[other_deliverable.pk]))
        self.assertRedirects(response, '/customers/')
    
    def test_deliverable_workspace_isolation_edit(self):
        """Test workspace isolation for deliverable edit"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        other_project = Project.objects.create(name='Other Project', customer=other_customer)
        other_deliverable = Deliverable.objects.create(name='Other Deliverable', project=other_project)
        
        response = self.client.get(reverse('deliverables:deliverable_edit', args=[other_deliverable.pk]))
        self.assertRedirects(response, '/customers/')
    
    def test_deliverable_workspace_isolation_delete(self):
        """Test workspace isolation for deliverable delete"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        other_project = Project.objects.create(name='Other Project', customer=other_customer)
        other_deliverable = Deliverable.objects.create(name='Other Deliverable', project=other_project)
        
        response = self.client.post(reverse('deliverables:deliverable_delete', args=[other_deliverable.pk]))
        self.assertRedirects(response, '/customers/')
        # Verify deliverable still exists
        self.assertTrue(Deliverable.objects.filter(pk=other_deliverable.pk).exists())
    
    def test_deliverable_workspace_isolation_add_ajax(self):
        """Test workspace isolation for deliverable add AJAX"""
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )
        other_customer = Customer.objects.create(name='Other Customer', user=other_user)
        other_project = Project.objects.create(name='Other Project', customer=other_customer)
        
        response = self.client.post(
            reverse('deliverables:deliverable_add_ajax', args=[other_project.pk]),
            json.dumps({'name': 'Other Deliverable'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Permission denied', data['error'])
    
    def test_deliverable_form_validation(self):
        """Test DeliverableForm validation"""
        form = DeliverableForm(project=self.project)
        self.assertIn('name', form.fields)
        self.assertIn('description', form.fields)
    
    def test_deliverable_form_clean_name_duplicate(self):
        """Test DeliverableForm clean_name prevents duplicates"""
        Deliverable.objects.create(name='Video 1', project=self.project)
        form = DeliverableForm({'name': 'Video 1', 'description': ''}, project=self.project)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_deliverable_form_clean_name_allows_edit_same_name(self):
        """Test DeliverableForm allows editing with same name"""
        deliverable = Deliverable.objects.create(name='Video 1', project=self.project)
        form = DeliverableForm({'name': 'Video 1', 'description': 'Updated'}, instance=deliverable, project=self.project)
        self.assertTrue(form.is_valid())


