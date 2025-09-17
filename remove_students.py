#!/usr/bin/env python3
"""
Script to remove specific students from TY-CS-A class and then remove the entire class
Removes students with roll numbers: 01, 02, 03, then removes TY-CS-A class completely
"""

import sqlite3
import os

def remove_ty_cs_a_class():
    db_path = 'attendance.db'
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting cleanup of TY-CS-A class...")
        
        # First, let's see what we're about to remove
        cursor.execute("""
            SELECT student_id, roll_no, name, class 
            FROM students 
            WHERE class = 'TY-CS-A'
        """)
        
        all_ty_cs_a_students = cursor.fetchall()
        
        if not all_ty_cs_a_students:
            print("No students found in TY-CS-A class")
            return
        
        print(f"Found {len(all_ty_cs_a_students)} students in TY-CS-A class:")
        for student in all_ty_cs_a_students:
            print(f"  - Roll: {student[1]}, Name: {student[2]}, Class: {student[3]}")
        
        # Get student IDs for deletion
        student_ids = [str(student[0]) for student in all_ty_cs_a_students]
        student_ids_str = ','.join(student_ids)
        
        # Remove attendance records first (due to foreign key constraints)
        cursor.execute(f"""
            DELETE FROM attendance 
            WHERE student_id IN ({student_ids_str})
        """)
        attendance_removed = cursor.rowcount
        print(f"Removed {attendance_removed} attendance records")
        
        # Remove the students
        cursor.execute(f"""
            DELETE FROM students 
            WHERE student_id IN ({student_ids_str})
        """)
        students_removed = cursor.rowcount
        print(f"Removed {students_removed} students")
        
        # Remove teacher assignments for TY-CS-A class
        cursor.execute("DELETE FROM teacher_assignments WHERE class = 'TY-CS-A'")
        assignments_removed = cursor.rowcount
        print(f"Removed {assignments_removed} teacher assignments")
        
        # Remove any remaining attendance records by class (in case some weren't caught above)
        cursor.execute("DELETE FROM attendance WHERE class = 'TY-CS-A'")
        remaining_attendance_removed = cursor.rowcount
        if remaining_attendance_removed > 0:
            print(f"Removed {remaining_attendance_removed} additional attendance records")
        
        # Commit the changes
        conn.commit()
        print(f"\n✅ Successfully removed TY-CS-A class completely!")
        print(f"  - Students removed: {students_removed}")
        print(f"  - Attendance records removed: {attendance_removed + remaining_attendance_removed}")
        print(f"  - Teacher assignments removed: {assignments_removed}")
        print("Database updated successfully!")
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("JSPM Attendance Tracker - TY-CS-A Class Cleanup")
    print("=" * 50)
    
    # Ask for confirmation
    response = input("Are you sure you want to remove the ENTIRE TY-CS-A class and all its students? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        remove_ty_cs_a_class()
    else:
        print("Operation cancelled.")
    
    print("\nPress Enter to exit...")
    input()
