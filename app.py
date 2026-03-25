import os, threading, uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
from converter import convert

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

jobs = {}

def run_job(job_id, input_path, title, mode, do_ocr, lang, make_epub, make_pdf):
    log_list = jobs[job_id]['log']
    def log(msg): log_list.append(msg); print(msg)
    jobs[job_id]['status'] = 'running'
    output_dir = Path(app.config['OUTPUT_FOLDER']) / job_id
    try:
        outputs = convert(
            input_pdf=Path(input_path),
            output_dir=output_dir,
            title=title or None,
            mode=mode,
            do_ocr=do_ocr,
            lang=lang,
            make_epub=make_epub,
            make_pdf=make_pdf,
            log=log,
        )
        jobs[job_id]['status'] = 'done'
        jobs[job_id]['outputs'] = outputs
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        log(f"❌ Hata: {e}")

@app.route('/')
def index(): return render_template('index.html')

@app.route('/convert', methods=['POST'])
def start_convert():
    if 'file' not in request.files: return jsonify({'error': 'Dosya yok'}), 400
    f = request.files['file']
    if not f.filename.lower().endswith('.pdf'): return jsonify({'error': 'Sadece PDF'}), 400
    job_id = str(uuid.uuid4())[:8]
    upload_path = Path(app.config['UPLOAD_FOLDER']) / f"{job_id}_{f.filename}"
    f.save(upload_path)
    mode      = request.form.get('mode', 'preserve')
    lang      = request.form.get('lang', 'tur+eng')
    title     = request.form.get('title', '').strip()
    do_ocr    = True
    make_epub = request.form.get('epub', 'false') == 'true'
    make_pdf  = request.form.get('pdf', 'true') == 'true'
    jobs[job_id] = {'status': 'queued', 'log': [], 'outputs': [], 'error': ''}
    threading.Thread(target=run_job, args=(job_id, upload_path, title, mode, do_ocr, lang, make_epub, make_pdf), daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job: return jsonify({'error': 'Job bulunamadı'}), 404
    return jsonify(job)

@app.route('/download/<job_id>/<filename>')
def download(job_id, filename):
    job = jobs.get(job_id)
    if not job: return jsonify({'error': 'Job bulunamadı'}), 404
    for out in job.get('outputs', []):
        if out['name'] == filename:
            return send_file(out['path'], as_attachment=True, download_name=filename)
    return jsonify({'error': 'Dosya bulunamadı'}), 404

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    print("BookForge → http://localhost:5000")
    app.run(debug=True, port=5000)
