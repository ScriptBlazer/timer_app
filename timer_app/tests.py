from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from .models import (
    Customer, Project, Timer, ProjectTimer, TimerSession,
    TeamMember, PendingRegistration,
    get_workspace_owner, is_workspace_owner, get_workspace_users
)


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
    
    def test_customer_total_duration_empty(self):
        """Test customer total duration with no projects"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.assertEqual(customer.total_duration_seconds(), 0)
    
    def test_customer_total_cost_empty(self):
        """Test customer total cost with no projects"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        self.assertEqual(customer.total_cost(), 0)


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
    
    def test_project_default_status(self):
        """Test project defaults to active status"""
        project = Project.objects.create(
            name='Test Project',
            customer=self.customer
        )
        self.assertEqual(project.status, 'active')
    
    def test_project_total_duration_empty(self):
        """Test project total duration with no timers"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        self.assertEqual(project.total_duration_seconds(), 0)
    
    def test_project_total_cost_empty(self):
        """Test project total cost with no timers"""
        project = Project.objects.create(name='Test Project', customer=self.customer)
        self.assertEqual(project.total_cost(), 0)


class TimerModelTest(TestCase):
    """Test Timer model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_timer_creation(self):
        """Test creating a timer"""
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        self.assertEqual(str(timer), 'Development')
        self.assertEqual(timer.user, self.user)
        self.assertEqual(float(timer.price_per_hour), 100.00)


class ProjectTimerModelTest(TestCase):
    """Test ProjectTimer model"""
    
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
    
    def test_project_timer_creation(self):
        """Test creating a project timer"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        self.assertEqual(project_timer.project, self.project)
        self.assertEqual(project_timer.timer, self.timer)
    
    def test_project_timer_is_running_false(self):
        """Test is_running returns False when no active session"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        self.assertFalse(project_timer.is_running())
    
    def test_project_timer_total_duration_empty(self):
        """Test total duration with no sessions"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        self.assertEqual(project_timer.total_duration_seconds(), 0)
    
    def test_project_timer_total_cost_empty(self):
        """Test total cost with no sessions"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        self.assertEqual(project_timer.total_cost(), 0)


class TimerSessionModelTest(TestCase):
    """Test TimerSession model"""
    
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
    
    def test_timer_session_creation(self):
        """Test creating a timer session"""
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now()
        )
        self.assertIsNotNone(session.start_time)
        self.assertIsNone(session.end_time)
    
    def test_timer_session_duration_seconds(self):
        """Test calculating session duration"""
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now()
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        duration = session.duration_seconds()
        self.assertAlmostEqual(duration, 7200, delta=1)  # 2 hours in seconds
    
    def test_timer_session_cost(self):
        """Test calculating session cost"""
        start_time = timezone.now() - timedelta(hours=2)
        end_time = timezone.now()
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        cost = session.cost()
        self.assertEqual(cost, 200.00)  # 2 hours * $100/hour
    
    def test_timer_session_cost_running(self):
        """Test cost returns 0 for running session"""
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=1)
            # end_time is None (still running)
        )
        self.assertEqual(session.cost(), 0)


class WorkspaceHelperTest(TestCase):
    """Test workspace helper functions"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            username='member',
            password='testpass123'
        )
    
    def test_is_workspace_owner_true(self):
        """Test user is workspace owner when not a team member"""
        self.assertTrue(is_workspace_owner(self.owner))
    
    def test_is_workspace_owner_false(self):
        """Test user is not workspace owner when they are a team member"""
        TeamMember.objects.create(owner=self.owner, member=self.member)
        self.assertFalse(is_workspace_owner(self.member))
    
    def test_get_workspace_owner_self(self):
        """Test getting workspace owner returns self for owner"""
        owner = get_workspace_owner(self.owner)
        self.assertEqual(owner, self.owner)
    
    def test_get_workspace_owner_team_member(self):
        """Test getting workspace owner returns owner for team member"""
        TeamMember.objects.create(owner=self.owner, member=self.member)
        owner = get_workspace_owner(self.member)
        self.assertEqual(owner, self.owner)
    
    def test_get_workspace_users(self):
        """Test getting all users in workspace"""
        TeamMember.objects.create(owner=self.owner, member=self.member)
        workspace_users = get_workspace_users(self.owner)
        self.assertIn(self.owner, workspace_users)
        self.assertIn(self.member, workspace_users)


class TeamMemberModelTest(TestCase):
    """Test TeamMember model"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            password='testpass123'
        )
        self.member = User.objects.create_user(
            username='member',
            password='testpass123'
        )
    
    def test_team_member_creation(self):
        """Test creating a team member"""
        team_member = TeamMember.objects.create(
            owner=self.owner,
            member=self.member,
            role='member'
        )
        self.assertEqual(team_member.owner, self.owner)
        self.assertEqual(team_member.member, self.member)
        self.assertEqual(team_member.role, 'member')


class PendingRegistrationModelTest(TestCase):
    """Test PendingRegistration model"""
    
    def test_pending_registration_creation(self):
        """Test creating a pending registration"""
        pending = PendingRegistration.objects.create(
            username='newuser',
            email='newuser@example.com',
            password_hash='hashed_password_here'
        )
        self.assertEqual(str(pending), 'Pending: newuser')
        self.assertIsNotNone(pending.approval_token)
        self.assertIsNotNone(pending.created_at)


class ViewAccessTest(TestCase):
    """Test view access and authentication"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_home_redirects_to_login_when_not_authenticated(self):
        """Test home redirects to login when not logged in"""
        response = self.client.get('/')
        self.assertRedirects(response, '/login/')
    
    def test_home_redirects_to_customers_when_authenticated(self):
        """Test home redirects to customers when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/')
        self.assertRedirects(response, '/customers/')
    
    def test_customer_list_requires_login(self):
        """Test customer list requires authentication"""
        response = self.client.get('/customers/')
        self.assertRedirects(response, '/login/?next=/customers/')
    
    def test_customer_list_accessible_when_logged_in(self):
        """Test customer list is accessible when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/customers/')
        self.assertEqual(response.status_code, 200)
    
    def test_login_page_accessible(self):
        """Test login page is accessible"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_register_page_accessible(self):
        """Test register page is accessible"""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)


class CustomerCRUDTest(TestCase):
    """Test Customer CRUD operations"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_customer(self):
        """Test creating a customer via form"""
        response = self.client.post('/customers/add/', {
            'name': 'New Customer'
        })
        # After creation, redirects to customer detail page
        customer = Customer.objects.get(name='New Customer')
        self.assertRedirects(response, f'/customers/{customer.pk}/')
        self.assertTrue(Customer.objects.filter(name='New Customer').exists())
    
    def test_view_customer_detail(self):
        """Test viewing customer detail"""
        customer = Customer.objects.create(name='Test Customer', user=self.user)
        response = self.client.get(f'/customers/{customer.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Customer')
    
    def test_edit_customer(self):
        """Test editing a customer"""
        customer = Customer.objects.create(name='Old Name', user=self.user)
        response = self.client.post(f'/customers/{customer.pk}/edit/', {
            'name': 'New Name'
        })
        self.assertRedirects(response, f'/customers/{customer.pk}/')
        customer.refresh_from_db()
        self.assertEqual(customer.name, 'New Name')


class IntegrationTest(TestCase):
    """Integration tests for complete workflows"""
    
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
    
    def test_complete_timer_workflow(self):
        """Test complete workflow: create session, calculate totals"""
        # Create a completed session
        start_time = timezone.now() - timedelta(hours=3)
        end_time = timezone.now()
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=start_time,
            end_time=end_time
        )
        
        # Check session cost
        self.assertEqual(session.cost(), 300.00)  # 3 hours * $100
        
        # Check project timer totals
        self.assertAlmostEqual(
            self.project_timer.total_duration_seconds(),
            10800,  # 3 hours in seconds
            delta=1
        )
        self.assertEqual(self.project_timer.total_cost(), 300.00)
        
        # Check project totals
        self.assertAlmostEqual(
            self.project.total_duration_seconds(),
            10800,
            delta=1
        )
        self.assertEqual(self.project.total_cost(), 300.00)
        
        # Check customer totals
        self.assertAlmostEqual(
            self.customer.total_duration_seconds(),
            10800,
            delta=1
        )
        self.assertEqual(self.customer.total_cost(), 300.00)
