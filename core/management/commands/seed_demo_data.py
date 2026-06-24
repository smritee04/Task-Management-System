"""
Creates a small set of demo accounts and sample tasks so reviewers can
explore the system immediately after first setup, without hand-creating
users through the admin panel.

Usage:
    python manage.py seed_demo_data

Safe to re-run: uses get_or_create throughout.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User, Domain
from tasks.models import Task, Project


class Command(BaseCommand):
    help = "Seed the database with demo admin/supervisor/intern accounts and sample tasks."

    def handle(self, *args, **options):
        domain, _ = Domain.objects.get_or_create(
            name="Web Development",
            defaults={"description": "Front-end and back-end web engineering work."},
        )

        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "first_name": "Ada",
                "last_name": "Admin",
            },
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin: admin / AdminPass123!"))

        supervisor, created = User.objects.get_or_create(
            username="supervisor1",
            defaults={
                "email": "supervisor1@example.com",
                "role": User.Role.SUPERVISOR,
                "first_name": "Sam",
                "last_name": "Supervisor",
            },
        )
        if created:
            supervisor.set_password("SuperPass123!")
            supervisor.save()
            self.stdout.write(self.style.SUCCESS("Created supervisor: supervisor1 / SuperPass123!"))

        intern, created = User.objects.get_or_create(
            username="intern1",
            defaults={
                "email": "intern1@example.com",
                "role": User.Role.INTERN,
                "first_name": "Ivy",
                "last_name": "Intern",
                "supervisor": supervisor,
                "domain": domain,
            },
        )
        if created:
            intern.set_password("InternPass123!")
            intern.save()
            self.stdout.write(self.style.SUCCESS("Created intern: intern1 / InternPass123!"))

        project, created = Project.objects.get_or_create(
            name="Internship Portal Revamp",
            defaults={
                "description": "Modernize the internship portal's UI and onboarding flow.",
                "status": Project.Status.ACTIVE,
                "created_by": supervisor,
                "start_date": timezone.now().date(),
                "deadline": (timezone.now() + timedelta(days=30)).date(),
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created sample project."))

        if not Task.objects.filter(title="Set up development environment").exists():
            Task.objects.create(
                project=project,
                title="Set up development environment",
                description="Install dependencies and get the local environment running.",
                created_by=supervisor,
                assigned_to=intern,
                priority=Task.Priority.MEDIUM,
                status=Task.Status.IN_PROGRESS,
                progress_percent=40,
                deadline=timezone.now() + timedelta(days=3),
            )
            self.stdout.write(self.style.SUCCESS("Created sample task."))

        self.stdout.write(self.style.SUCCESS("Seed complete."))
