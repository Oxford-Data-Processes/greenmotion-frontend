from fastapi import FastAPI
import json
from fastapi.responses import JSONResponse
import os
from datetime import datetime

app = FastAPI()


@app.get("/table={table_name}/limit={limit}")
async def read_item(table_name: str, limit: int):
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, "app/v2/api/data")
    file_path = os.path.join(data_directory, f"{table_name}_processed_limit_5.json")
    with open(file_path) as f:
        data = json.load(f)
    filtered_data = data[:limit]
    return JSONResponse(content=filtered_data)


@app.get("/table={table_name}/start_date={start_date}/end_date={end_date}")
async def read_item_by_date(table_name: str, start_date: str, end_date: str):
    current_directory = os.getcwd()
    data_directory = os.path.join(current_directory, "app/v2/api/data")
    file_path = os.path.join(data_directory, f"{table_name}_processed_limit_5.json")
    with open(file_path) as f:
        data = json.load(f)
    
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    
    filtered_data = [
        item for item in data
        if start_date <= datetime.strptime(item["pickup_datetime"][:10], "%Y-%m-%d") <= end_date
    ]
    
    return JSONResponse(content=filtered_data)
