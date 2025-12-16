from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from customers.models import Customer
from projects.models import Project

from .models import (
    Timer, ProjectTimer, TimerSession,
    TeamMember, PendingRegistration,
    get_workspace_owner, is_workspace_owner, get_workspace_users
)


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
        self.assertIsNotNone(timer.created_at)
        self.assertIsNotNone(timer.updated_at)
    
    def test_timer_default_color(self):
        """Test timer has default header color"""
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00
        )
        self.assertEqual(timer.header_color, '#3498db')
    
    def test_timer_custom_color(self):
        """Test timer with custom header color"""
        timer = Timer.objects.create(
            task_name='Development',
            user=self.user,
            price_per_hour=100.00,
            header_color='#ff0000'
        )
        self.assertEqual(timer.header_color, '#ff0000')
    
    def test_timer_ordering(self):
        """Test timer ordering by task_name"""
        Timer.objects.create(task_name='Zebra Task', user=self.user, price_per_hour=100.00)
        Timer.objects.create(task_name='Alpha Task', user=self.user, price_per_hour=100.00)
        timers = Timer.objects.all()
        self.assertEqual(timers[0].task_name, 'Alpha Task')
        self.assertEqual(timers[1].task_name, 'Zebra Task')


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
        self.assertIsNotNone(project_timer.created_at)
    
    def test_project_timer_is_running_false(self):
        """Test is_running returns False when no active session"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        self.assertFalse(project_timer.is_running())
    
    def test_project_timer_is_running_true(self):
        """Test is_running returns True when active session exists"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=timezone.now()
        )
        self.assertTrue(project_timer.is_running())
    
    def test_project_timer_active_session(self):
        """Test active_session returns the active session"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        active = TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=timezone.now()
        )
        self.assertEqual(project_timer.active_session(), active)
    
    def test_project_timer_current_duration_seconds(self):
        """Test current_duration_seconds for running timer"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        start_time = timezone.now() - timedelta(hours=2)
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start_time
        )
        duration = project_timer.current_duration_seconds()
        self.assertAlmostEqual(duration, 7200, delta=10)  # 2 hours in seconds
    
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
    
    def test_project_timer_total_duration_with_sessions(self):
        """Test total duration calculation with multiple sessions"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        # Create two completed sessions
        start1 = timezone.now() - timedelta(hours=3)
        end1 = start1 + timedelta(hours=1)
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start1,
            end_time=end1
        )
        start2 = timezone.now() - timedelta(hours=1)
        end2 = start2 + timedelta(hours=2)
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start2,
            end_time=end2
        )
        # Total should be 3 hours (1 + 2)
        self.assertAlmostEqual(project_timer.total_duration_seconds(), 10800, delta=1)
    
    def test_project_timer_total_cost_with_sessions(self):
        """Test total cost calculation with multiple sessions"""
        project_timer = ProjectTimer.objects.create(
            project=self.project,
            timer=self.timer
        )
        # Create two completed sessions with different prices
        start1 = timezone.now() - timedelta(hours=2)
        end1 = start1 + timedelta(hours=1)
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=100.00,
            start_time=start1,
            end_time=end1
        )
        start2 = timezone.now() - timedelta(hours=1)
        end2 = start2 + timedelta(hours=1)
        TimerSession.objects.create(
            project_timer=project_timer,
            price_per_hour=150.00,  # Different price
            start_time=start2,
            end_time=end2
        )
        # Total should be $250 (1 hour * $100 + 1 hour * $150)
        self.assertEqual(project_timer.total_cost(), 250.00)


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
        self.assertEqual(float(session.price_per_hour), 100.00)
    
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
    
    def test_timer_session_duration_running(self):
        """Test calculating duration for running session"""
        start_time = timezone.now() - timedelta(hours=1)
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=start_time
            # end_time is None (still running)
        )
        duration = session.duration_seconds()
        self.assertAlmostEqual(duration, 3600, delta=10)  # Approximately 1 hour
    
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
    
    def test_timer_session_price_snapshot(self):
        """Test session uses price snapshot, not current timer price"""
        session = TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now()
        )
        # Change timer price
        self.timer.price_per_hour = 150.00
        self.timer.save()
        # Session cost should still use original price
        self.assertEqual(session.cost(), 100.00)  # 1 hour * $100 (snapshot price)


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
    
    def test_get_workspace_users_single(self):
        """Test getting workspace users for single user"""
        workspace_users = get_workspace_users(self.owner)
        self.assertIn(self.owner, workspace_users)
        self.assertNotIn(self.member, workspace_users)


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
        self.assertIsNotNone(team_member.created_at)
    
    def test_team_member_default_role(self):
        """Test team member defaults to member role"""
        team_member = TeamMember.objects.create(
            owner=self.owner,
            member=self.member
        )
        self.assertEqual(team_member.role, 'member')
    
    def test_team_member_unique_together(self):
        """Test team member unique constraint"""
        TeamMember.objects.create(owner=self.owner, member=self.member)
        # Should not be able to create duplicate
        with self.assertRaises(Exception):
            TeamMember.objects.create(owner=self.owner, member=self.member)


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
    
    def test_pending_registration_unique_username(self):
        """Test pending registration requires unique username"""
        PendingRegistration.objects.create(
            username='newuser',
            email='newuser@example.com',
            password_hash='hash1'
        )
        # Should not be able to create duplicate username
        with self.assertRaises(Exception):
            PendingRegistration.objects.create(
                username='newuser',
                email='other@example.com',
                password_hash='hash2'
            )


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
    
    def test_login_page_accessible(self):
        """Test login page is accessible"""
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
    
    def test_register_page_accessible(self):
        """Test register page is accessible"""
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)
    
    def test_timer_list_requires_login(self):
        """Test timer list requires authentication"""
        response = self.client.get('/timers/')
        self.assertRedirects(response, '/login/?next=/timers/')
    
    def test_timer_list_accessible_when_logged_in(self):
        """Test timer list is accessible when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/timers/')
        self.assertEqual(response.status_code, 200)
    
    def test_running_timers_requires_login(self):
        """Test running timers requires authentication"""
        response = self.client.get('/timers/running/')
        self.assertRedirects(response, '/login/?next=/timers/running/')
    
    def test_running_timers_accessible_when_logged_in(self):
        """Test running timers is accessible when logged in"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/timers/running/')
        self.assertEqual(response.status_code, 200)
    
    def test_admin_panel_requires_login(self):
        """Test admin panel requires authentication"""
        response = self.client.get('/admin-panel/')
        self.assertRedirects(response, '/login/?next=/admin-panel/')


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
    
    def test_multiple_sessions_workflow(self):
        """Test workflow with multiple sessions across different timers"""
        # Create second timer
        timer2 = Timer.objects.create(
            task_name='Design',
            user=self.user,
            price_per_hour=80.00
        )
        project_timer2 = ProjectTimer.objects.create(
            project=self.project,
            timer=timer2
        )
        
        # Create sessions for both timers
        start1 = timezone.now() - timedelta(hours=2)
        end1 = start1 + timedelta(hours=1)
        TimerSession.objects.create(
            project_timer=self.project_timer,
            price_per_hour=100.00,
            start_time=start1,
            end_time=end1
        )
        
        start2 = timezone.now() - timedelta(hours=1)
        end2 = start2 + timedelta(hours=1)
        TimerSession.objects.create(
            project_timer=project_timer2,
            price_per_hour=80.00,
            start_time=start2,
            end_time=end2
        )
        
        # Project should have 2 hours total (1 + 1)
        self.assertAlmostEqual(self.project.total_duration_seconds(), 7200, delta=1)
        # Project should have $180 total ($100 + $80)
        self.assertEqual(self.project.total_cost(), 180.00)
