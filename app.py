import os
import socket
import uuid
from flask import Flask, request, redirect, render_template_string
import boto3

app = Flask(__name__)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "Items-Erzhanov")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "tau-lab2-erzhanov-20041111")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3", region_name=AWS_REGION)

HTML = """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Облачный каталог</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 720px; margin: 30px auto; padding: 0 15px; }
    .banner { background: #eef6ff; border: 1px solid #99c2ff; padding: 10px 14px; border-radius: 6px; margin-bottom: 20px; }
    form { background: #f9f9f9; padding: 15px; border-radius: 6px; margin-bottom: 25px; border: 1px solid #ddd; }
    input, button { padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }
    button { background: #0066cc; color: white; border: none; cursor: pointer; font-weight: bold; }
    .item { border-bottom: 1px solid #eee; padding: 12px 0; }
  </style>
</head>
<body>
  <h1>Облачный каталог</h1>
  <div class="banner">
    <strong>Запрос обработал контейнер:</strong> {{ container_id }}
  </div>

  <form method="post" action="/add" enctype="multipart/form-data">
    <h3>Добавить запись</h3>
    <input type="text" name="title" placeholder="Название" required>
    <input type="text" name="description" placeholder="Описание" required>
    <input type="file" name="file">
    <button type="submit">Сохранить</button>
  </form>

  <h3>Записи в каталоге ({{ items|length }})</h3>
  {% for item in items %}
    <div class="item">
      <strong>{{ item.get('title', 'Без названия') }}</strong> — {{ item.get('description', '') }}
      {% if item.get('file_url') %}
        <br><a href="{{ item['file_url'] }}" target="_blank">Открыть прикреплённый файл</a>
      {% endif %}
    </div>
  {% endfor %}
</body>
</html>
"""

@app.route("/health")
def health():
    return {"status": "ok"}, 200

@app.route("/")
def index():
    container_id = socket.gethostname()
    try:
        resp = table.scan()
        items = resp.get("Items", [])
    except Exception as e:
        items = [{"title": "Ошибка чтения DynamoDB", "description": str(e)}]
    return render_template_string(HTML, items=items, container_id=container_id)

@app.route("/add", methods=["POST"])
def add_item():
    item_id = str(uuid.uuid4())
    title = request.form.get("title", "")
    description = request.form.get("description", "")
    file_obj = request.files.get("file")
    file_url = ""

    if file_obj and file_obj.filename:
        key = f"{item_id}_{file_obj.filename}"
        s3.upload_fileobj(file_obj, BUCKET_NAME, key)
        file_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": key},
            ExpiresIn=3600
        )

    # Попробуем записать с ключом 'id' (стандартный ключ в 3-й лабе)
    table.put_item(Item={
        "id": item_id,
        "title": title,
        "description": description,
        "file_url": file_url
    })
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
