from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
from database import init_db, save_prescription_result, list_prescriptions, get_prescription, update_prescription
from extractor import extract_text_from_image, extract_prescription_fields

app = Flask(__name__)
app.secret_key = 'medi-extract-secret'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'pdf'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
init_db()


@app.route('/')
def index():
    recent_records = list_prescriptions(limit=5)
    return render_template('index.html', recent_records=recent_records)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return redirect(url_for('index'))

    if 'file' not in request.files:
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))

    if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        extracted_data = extract_text_from_image(file_path)
        fields = extracted_data['fields']

        total_fields = 6
        wrong_fields = 0
        for key in ['patient_name', 'medicine', 'dosage', 'strength', 'frequency', 'duration']:
            if not fields.get(key, '').strip():
                wrong_fields += 1

        correct_fields = total_fields - wrong_fields
        accuracy = round((correct_fields / total_fields) * 100, 2) if total_fields else 0
        record_id = save_prescription_result(filename, extracted_data['ocr_text'], fields, accuracy)

        return redirect(url_for('result', record_id=record_id))

    return redirect(url_for('index'))


@app.route('/result/<int:record_id>')
def result(record_id):
    record = get_prescription(record_id)
    if not record:
        return redirect(url_for('index'))

    fields = {
        'patient_name': record.get('patient_name', ''),
        'medicine': record.get('medicine', ''),
        'dosage': record.get('dosage', ''),
        'strength': record.get('strength', ''),
        'frequency': record.get('frequency', ''),
        'duration': record.get('duration', ''),
    }

    return render_template(
        'result.html',
        filename=record.get('filename', ''),
        extracted_text=record.get('extracted_text', ''),
        extracted_fields=fields,
        wrong_fields=6 - sum(1 for value in fields.values() if value and value.strip()),
        accuracy=record.get('accuracy', 0),
        record_id=record_id,
    )


@app.route('/review/<int:record_id>', methods=['GET', 'POST'])
def review(record_id):
    record = get_prescription(record_id)
    if not record:
        return redirect(url_for('history'))

    if request.method == 'POST':
        fields = {
            'patient_name': request.form.get('patient_name', ''),
            'medicine': request.form.get('medicine', ''),
            'dosage': request.form.get('dosage', ''),
            'strength': request.form.get('strength', ''),
            'frequency': request.form.get('frequency', ''),
            'duration': request.form.get('duration', ''),
        }
        total_fields = 6
        wrong_fields = 0
        for key in ['patient_name', 'medicine', 'dosage', 'strength', 'frequency', 'duration']:
            if not fields.get(key, '').strip():
                wrong_fields += 1
        correct_fields = total_fields - wrong_fields
        accuracy = round((correct_fields / total_fields) * 100, 2) if total_fields else 0
        update_prescription(record_id, fields, accuracy)
        return redirect(url_for('review', record_id=record_id))

    return render_template('review.html', record=record)


@app.route('/dashboard')
def dashboard():
    records = list_prescriptions()
    total = len(records)
    average_accuracy = round(sum(item['accuracy'] or 0 for item in records) / total, 2) if total else 0
    recent = records[-5:] if records else []
    return render_template(
        'dashboard.html',
        total=total,
        average_accuracy=average_accuracy,
        recent=recent,
    )


@app.route('/history')
def history():
    query = request.args.get('query', '').strip()
    records = list_prescriptions(query=query)
    return render_template('history.html', records=records, query=query)


@app.route('/extract-text', methods=['POST'])
def extract_text():
    text = request.form.get('prescription_text', '').strip()
    if not text:
        return redirect(url_for('index'))

    fields = extract_prescription_fields(text)

    total_fields = 6
    wrong_fields = 0
    for key in ['patient_name', 'medicine', 'dosage', 'strength', 'frequency', 'duration']:
        if not fields.get(key, '').strip():
            wrong_fields += 1

    correct_fields = total_fields - wrong_fields
    accuracy = round((correct_fields / total_fields) * 100, 2) if total_fields else 0
    record_id = save_prescription_result('Pasted Text', text, fields, accuracy)

    return redirect(url_for('result', record_id=record_id))

    return redirect(url_for('result', record_id=record_id))


if __name__ == '__main__':
    app.run(debug=True)
