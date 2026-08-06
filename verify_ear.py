from app import app

with app.test_client() as client:
    for filename in ['prescription_1.jpg', 'prescription_2.jpg', 'prescription_3.jpg']:
        print(f"\n--- Uploading {filename} ---")
        with open(filename, 'rb') as f:
            response = client.post('/upload', data={'file': (f, filename)}, content_type='multipart/form-data')
        print(f"Status code: {response.status_code}")
        print(f"Redirect location: {response.headers.get('Location')}")
