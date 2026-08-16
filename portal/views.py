from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Q, Sum, Avg
from .models import StudentProfile, Course, Enrollment

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    try:
        profile = request.user.studentprofile
        enrollments = Enrollment.objects.filter(student=profile).select_related('course')
        
        total_credits = enrollments.aggregate(total=Sum('course__credits'))['total'] or 0
        
        # Simple GPA calculation (assuming letter grades)
        grade_points = {
            'A': 4.0, 'A-': 3.7,
            'B+': 3.3, 'B': 3.0, 'B-': 2.7,
            'C+': 2.3, 'C': 2.0, 'C-': 1.7,
            'D': 1.0, 'F': 0.0
        }
        
        total_points = 0
        graded_courses = 0
        for e in enrollments:
            if e.grade and e.grade.upper() in grade_points:
                total_points += grade_points[e.grade.upper()] * e.course.credits
                graded_courses += e.course.credits
        
        gpa = round(total_points / graded_courses, 2) if graded_courses > 0 else 0.0
        
    except StudentProfile.DoesNotExist:
        profile = None
        enrollments = []
        total_credits = 0
        gpa = 0.0

    return render(request, 'dashboard.html', {
        'profile': profile,
        'enrollments': enrollments,
        'total_credits': total_credits,
        'gpa': gpa,
        'enrolled_count': enrollments.count() if profile else 0
    })

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            StudentProfile.objects.create(
                user=user,
                student_id=f"STU{user.id:04d}",
                department="General",
                year=1
            )
            messages.success(request, 'Account created! You can now log in.')
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def course_list(request):
    query = request.GET.get('q', '')
    courses = Course.objects.all()
    
    if query:
        courses = courses.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
    
    # Get courses the current student is already enrolled in
    enrolled_course_ids = []
    if hasattr(request.user, 'studentprofile'):
        enrolled_course_ids = Enrollment.objects.filter(
            student=request.user.studentprofile
        ).values_list('course_id', flat=True)
    
    return render(request, 'courses.html', {
        'courses': courses,
        'query': query,
        'enrolled_course_ids': enrolled_course_ids
    })

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    profile = request.user.studentprofile
    
    enrollment, created = Enrollment.objects.get_or_create(
        student=profile,
        course=course
    )
    
    if created:
        messages.success(request, f'Successfully enrolled in {course.name}')
    else:
        messages.info(request, f'You are already enrolled in {course.name}')
    
    return redirect('course_list')

@login_required
def profile(request):
    profile = get_object_or_404(StudentProfile, user=request.user)
    
    if request.method == 'POST':
        profile.department = request.POST.get('department')
        profile.year = request.POST.get('year')
        profile.phone = request.POST.get('phone')
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    return render(request, 'profile.html', {'profile': profile})