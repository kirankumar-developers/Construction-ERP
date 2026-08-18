import requests

BASE_URL = "http://127.0.0.1:5000"

def test_flow():
    # 1. Login as Super Admin
    session = requests.Session()
    login_data = {
        'email': 'superadmin@onsiteerp.com',
        'password': 'admin123'
    }
    r = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    print(f"Login Response: {r.status_code}")
    assert r.status_code == 302, "Super Admin login failed"
    print("Logged in as Super Admin successfully.\n")

    # 2. Quick Create Client
    client_data = {
        'client_name': 'Test Automated Client',
        'company_name': 'Automated Co',
        'email': 'auto_client@test.com',
        'phone': '111-222-3333',
        'address': 'Auto Street',
        'city': 'Auto City',
        'state': 'Auto State',
        'country': 'Auto Country',
        'gst_details': 'GST-AUTO'
    }
    r_client = session.post(f"{BASE_URL}/clients/create-quick", data=client_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Create Client Response Status: {r_client.status_code}")
    print(f"Create Client JSON: {r_client.json()}")
    assert r_client.status_code == 200, "Client creation failed"
    client_json = r_client.json()
    assert client_json['success'] is True
    assert 'client' in client_json
    client_id = client_json['client']['id']
    print(f"Client created successfully with ID: {client_id}\n")

    # 3. Get Client List
    r_list = session.get(f"{BASE_URL}/clients/list", headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"List Clients Response Status: {r_list.status_code}")
    list_json = r_list.json()
    assert list_json['success'] is True
    clients = list_json['clients']
    found = False
    for c in clients:
        if c['id'] == client_id:
            found = True
            assert c['client_name'] == 'Test Automated Client'
            assert c['company_name'] == 'Automated Co'
            break
    assert found, "Created client was not found in client list"
    print("Verified client listing successfully.\n")

    # 4. Quick Create Project Manager
    pm_data = {
        'name': 'Test Automated PM',
        'email': 'auto_pm@test.com',
        'phone': '444-555-6666',
        'employee_id': 'EMP-AUTO-101',
        'department': 'Engineering',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    r_pm = session.post(f"{BASE_URL}/users/create-project-manager", data=pm_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Create PM Response Status: {r_pm.status_code}")
    print(f"Create PM JSON: {r_pm.json()}")
    assert r_pm.status_code == 200, "PM creation failed"
    pm_json = r_pm.json()
    assert pm_json['success'] is True
    pm_id = pm_json['project_manager']['id']
    print(f"PM created successfully with ID: {pm_id}\n")

    # 5. List Project Managers
    r_pm_list = session.get(f"{BASE_URL}/users/project-managers/list", headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"List PMs Response Status: {r_pm_list.status_code}")
    pm_list_json = r_pm_list.json()
    assert pm_list_json['success'] is True
    found_pm = False
    for p in pm_list_json['project_managers']:
        if p['id'] == pm_id:
            found_pm = True
            assert p['name'] == 'Test Automated PM'
            break
    assert found_pm, "Created PM was not found in PM list"
    print("Verified PM listing successfully.\n")

    # 6. Test Permissions with Unauthorized User (Dave Engineer)
    eng_session = requests.Session()
    eng_login_data = {
        'email': 'engineer@onsiteerp.com',
        'password': 'admin123'
    }
    r_eng_login = eng_session.post(f"{BASE_URL}/login", data=eng_login_data, allow_redirects=False)
    assert r_eng_login.status_code == 302, "Engineer login failed"
    print("Logged in as Engineer (unauthorized role).")

    # Client Creation (Should fail with 403)
    r_eng_client = eng_session.post(f"{BASE_URL}/clients/create-quick", data=client_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Engineer Create Client Status: {r_eng_client.status_code} (Expected 403)")
    assert r_eng_client.status_code == 403, "Engineer was incorrectly allowed to create client"

    # PM Creation (Should fail with 403)
    r_eng_pm = eng_session.post(f"{BASE_URL}/users/create-project-manager", data=pm_data, headers={'X-Requested-With': 'XMLHttpRequest'})
    print(f"Engineer Create PM Status: {r_eng_pm.status_code} (Expected 403)")
    assert r_eng_pm.status_code == 403, "Engineer was incorrectly allowed to create PM"

    print("\nAll integration tests passed successfully!")

if __name__ == "__main__":
    test_flow()
