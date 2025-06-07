from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import shutil
import os

from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o pon el origen específico como ["http://localhost:5000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de la base de datos MySQL
DATABASE_URL = "mysql+mysqlconnector://root@localhost/miapp"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Modelo de SQLAlchemy
class Tienda(Base):
    __tablename__ = 'tienda'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    description = Column(String(255))
    price = Column(Float)
    category = Column(String(100))
    image = Column(String(255))  # solo guardaremos el nombre del archivo o la ruta

Base.metadata.create_all(bind=engine)

# Ruta estática para servir imágenes
app.mount("/images", StaticFiles(directory="images"), name="images")

# Endpoint para subir producto con imagen
@app.post("/producto/")
async def create_product(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # Guardar imagen en la carpeta local
        image_path = f"images/{image.filename}"
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        db = SessionLocal()
        nuevo_producto = Tienda(
            title=title,
            description=description,
            price=price,
            category=category,
            image=image_path,
        )
        db.add(nuevo_producto)
        db.commit()
        db.refresh(nuevo_producto)
        return {
            "id": nuevo_producto.id,
            "title": nuevo_producto.title,
            "description": nuevo_producto.description,
            "price": nuevo_producto.price,
            "category": nuevo_producto.category,
            "image": f"http://localhost:8000/{image_path}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para obtener un producto
@app.get("/producto/{id}")
def get_producto(id: int):
    db = SessionLocal()
    producto = db.query(Tienda).filter(Tienda.id == id).first()
    if producto:
        return {
            "id": producto.id,
            "title": producto.title,
            "description": producto.description,
            "price": producto.price,
            "category": producto.category,
            "image": f"http://localhost:8000/{producto.image}",
        }
    else:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

# Endpoint para obtener todos los productos
@app.get("/productos")
def get_all_productos():
    db = SessionLocal()
    productos = db.query(Tienda).all()
    return [
        {
            "id": producto.id,
            "title": producto.title,
            "description": producto.description,
            "price": producto.price,
            "category": producto.category,
            "image": f"http://localhost:8000/{producto.image}",
        }
        for producto in productos
    ]
