import requests

BASE_URL = "http://127.0.0.1:5000"

def test_crud_and_permissions():
    # ----------------------------------------------------
    # 1. TEST AS SUPER ADMIN (Full Access)
    # ----------------------------------------------------
    print("=== Testing as Super Admin ===")
    sa_session = requests.Session()
    login_res = sa_session.post(f"{BASE_URL}/login", data={
        'email': 'superadmin@onsiteerp.com',
        'password': 'admin123'
    }, allow_redirects=False)
    assert login_res.status_code == 302, "Super Admin login failed"
    print("Login successful.")

    # 1.1 List PMs
    r_list = sa_session.get(f"{BASE_URL}/project-managers/")
    print(f"List PMs Status: {r_list.status_code}")
    assert r_list.status_code == 200

    # 1.2 Quick Create PM
    pm_quick_data = {
        'name': 'Quick PM Admin',
        'email': 'quick_pm_admin@test.com',
        'phone': '123-123-1234',
        'employee_id': 'EMP-Q-999',
        'department': 'Civil',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    r_quick = sa_session.post(f"{BASE_URL}/project-managers/quick-create", data=pm_quick_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Quick Create PM Status: {r_quick.status_code}")
    print(f"Quick Create JSON: {r_quick.json()}")
    assert r_quick.status_code == 200
    quick_json = r_quick.json()
    assert quick_json['success'] is True
    assert 'project_manager' in quick_json
    pm_id = quick_json['project_manager']['id']
    print(f"Created PM with ID: {pm_id}")

    # 1.3 Check duplicate email check
    r_dup_email = sa_session.post(f"{BASE_URL}/project-managers/quick-create", data=pm_quick_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Dup Email Status: {r_dup_email.status_code} (Expected 400)")
    assert r_dup_email.status_code == 400
    assert "Email already exists" in r_dup_email.json()['message']

    # 1.4 Check duplicate employee ID check
    pm_dup_emp_id = pm_quick_data.copy()
    pm_dup_emp_id['email'] = 'another_email@test.com'
    r_dup_emp = sa_session.post(f"{BASE_URL}/project-managers/quick-create", data=pm_dup_emp_id, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Dup Emp ID Status: {r_dup_emp.status_code} (Expected 400)")
    assert r_dup_emp.status_code == 400
    assert "Employee ID already exists" in r_dup_emp.json()['message']

    # 1.5 View PM details
    r_view = sa_session.get(f"{BASE_URL}/project-managers/{pm_id}/view")
    print(f"View PM Details Status: {r_view.status_code}")
    assert r_view.status_code == 200

    # 1.6 Edit PM details
    pm_edit_data = {
        'name': 'Quick PM Admin Updated',
        'email': 'quick_pm_admin@test.com',
        'phone': '999-999-9999',
        'employee_id': 'EMP-Q-999',
        'department': 'Civil (Operations)'
    }
    r_edit = sa_session.post(f"{BASE_URL}/project-managers/{pm_id}/edit", data=pm_edit_data, allow_redirects=False)
    print(f"Edit PM Details Status: {r_edit.status_code}")
    assert r_edit.status_code in [200, 302]

    # 1.7 Toggle Status (Deactivate / Activate)
    r_toggle = sa_session.post(f"{BASE_URL}/project-managers/{pm_id}/toggle-status", allow_redirects=False)
    print(f"Toggle PM Status: {r_toggle.status_code}")
    assert r_toggle.status_code in [200, 302]

    # 1.8 Delete PM (Only Super Admin)
    r_delete = sa_session.post(f"{BASE_URL}/project-managers/{pm_id}/delete", allow_redirects=False)
    print(f"Delete PM Status: {r_delete.status_code}")
    assert r_delete.status_code in [200, 302]
    print("Delete successful as Super Admin.\n")


    # ----------------------------------------------------
    # 2. TEST AS ADMIN (Can do everything except delete)
    # ----------------------------------------------------
    print("=== Testing as Admin ===")
    admin_session = requests.Session()
    login_res = admin_session.post(f"{BASE_URL}/login", data={
        'email': 'admin@onsiteerp.com',
        'password': 'admin123'
    }, allow_redirects=False)
    assert login_res.status_code == 302, "Admin login failed"
    print("Login successful.")

    # 2.1 Quick Create PM as Admin
    pm_admin_data = {
        'name': 'Quick PM created by Admin',
        'email': 'pm_by_admin@test.com',
        'phone': '111-222-3333',
        'employee_id': 'EMP-A-888',
        'department': 'Civil',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    r_quick_a = admin_session.post(f"{BASE_URL}/project-managers/quick-create", data=pm_admin_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Admin Quick Create PM Status: {r_quick_a.status_code}")
    assert r_quick_a.status_code == 200
    pm_id_a = r_quick_a.json()['project_manager']['id']
    print(f"Created PM with ID: {pm_id_a}")

    # 2.2 Attempt to Delete as Admin (Should fail with 403)
    r_delete_a = admin_session.post(f"{BASE_URL}/project-managers/{pm_id_a}/delete", allow_redirects=False)
    print(f"Admin Delete PM Status: {r_delete_a.status_code} (Expected 403)")
    assert r_delete_a.status_code == 403
    print("Delete blocked for Admin role.\n")


    # ----------------------------------------------------
    # 3. TEST AS UNAUTHORIZED ROLE (Engineer)
    # ----------------------------------------------------
    print("=== Testing as Engineer ===")
    eng_session = requests.Session()
    login_res = eng_session.post(f"{BASE_URL}/login", data={
        'email': 'engineer@onsiteerp.com',
        'password': 'admin123'
    }, allow_redirects=False)
    assert login_res.status_code == 302, "Engineer login failed"
    print("Login successful.")

    # 3.1 Attempt List (Should fail with 403)
    r_eng_list = eng_session.get(f"{BASE_URL}/project-managers/", headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Engineer List PM Status: {r_eng_list.status_code} (Expected 403)")
    assert r_eng_list.status_code == 403

    # 3.2 Attempt Quick Create (Should fail with 403)
    r_eng_quick = eng_session.post(f"{BASE_URL}/project-managers/quick-create", data=pm_quick_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Engineer Quick Create Status: {r_eng_quick.status_code} (Expected 403)")
    assert r_eng_quick.status_code == 403

    print("\nAll PM CRUD and permission integration tests passed successfully!")

if __name__ == "__main__":
    test_crud_and_permissions()
