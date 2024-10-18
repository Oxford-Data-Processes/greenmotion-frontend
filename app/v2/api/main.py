from fastapi import FastAPI
import json
from fastapi.responses import JSONResponse
import os

app = FastAPI()


@app.get("/table={table_name}/limit={limit}")
async def read_item(table_name: str, limit: int):
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, "app/v2/api/data")
    file_path = os.path.join(data_directory, f"{table_name}_processed_limit_5.json")
    print(f"Current directory: {data_directory}")
    print(f"File path: {file_path}")
    with open(file_path) as f:
        data = json.load(f)
    filtered_data = data[:limit]
    return JSONResponse(content=filtered_data)
