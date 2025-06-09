from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import shutil
import os
from typing import List
from pydantic import EmailStr
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # o pon el origen específico como ["http://localhost:5000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de la base de datos MySQL
DATABASE_URL = "mysql+pymysql://root@localhost:3306/tienda"
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
    media = Column(String(1000))  # solo guardaremos el nombre del archivo o la ruta

class Usuario(Base):
    __tablename__ = 'usuarios'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(191), unique=True, index=True)
    password = Column(String(255))  # Idealmente con hash

class Carrito(Base):
    __tablename__ = 'carrito'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('usuarios.id'))
    producto_id = Column(Integer, ForeignKey('tienda.id'))

class Favorito(Base):
    __tablename__ = 'favoritos'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('usuarios.id'))
    producto_id = Column(Integer, ForeignKey('tienda.id'))

class Compra(Base):
    __tablename__ = 'compras'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('usuarios.id'))
    producto_id = Column(Integer, ForeignKey('tienda.id'))
    fecha = Column(DateTime, default=datetime.now)
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
    media: List[UploadFile] = File(...)
):
    try:
        saved_files = []
        # Guardar imagen en la carpeta local
        for file in media:
            path = f"images/{file.filename}"  # puedes renombrar para evitar duplicados
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_files.append(f"http://localhost:8000/{path}")

        db = SessionLocal()
        nuevo_producto = Tienda(
            title=title,
            description=description,
            price=price,
            category=category,
            media=",".join(saved_files), # guarda como string separado por comas
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
            "media": saved_files,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint para obtener un producto
@app.get("/producto/{id}")
def get_producto(id: int):
    db = SessionLocal()
    producto = db.query(Tienda).filter(Tienda.id == id).first()
    if producto:
        media_urls = producto.media.split(",")
        return {
            "id": producto.id,
            "title": producto.title,
            "description": producto.description,
            "price": producto.price,
            "category": producto.category,
            "media": media_urls,
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
            "media": producto.media.split(","),
        }
        for producto in productos
    ]

# * Autenticacion
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.post("/register")
def register_user(name: str = Form(...) ,email: EmailStr = Form(...), password: str = Form(...)):
    db = SessionLocal()
    hashed = hash_password(password)
    exist = db.query(Usuario).filter(Usuario.email == email).first()
    if exist:
        raise HTTPException(status_code= 404, detail="EL usuario con ese correo ya existe")
    user = Usuario(name = name, email=email, password=hashed)
    db.add(user)
    db.commit()
    return {"msg": "Usuario registrado"}


#* Favoritos
@app.post("/favoritos/")
def add_favorito(user_id: int, producto_id: int):
    db = SessionLocal()
    fav = Favorito(user_id=user_id, producto_id=producto_id)
    db.add(fav)
    db.commit()
    return {"msg": "Agregado a favoritos"}

@app.get("/favoritos/{user_id}")
def get_favoritos(user_id: int):
    db = SessionLocal()
    favs = db.query(Favorito).filter(Favorito.user_id == user_id).all()
    return [{"producto_id": f.producto_id} for f in favs]

@app.delete("/favoritos/{user_id}")
def delete_favoritos(user_id: int):
    db = SessionLocal()
    exist = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not exist:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete()
    db.commit()
    return {"message": "usuario eliminado"}

#* Carrito
@app.post("/carrito/")
def add_to_cart(user_id: int, producto_id: int):
    db = SessionLocal()
    item = Carrito(user_id=user_id, producto_id=producto_id)
    db.add(item)
    db.commit()
    return {"msg": "Producto agregado al carrito"}

@app.get("/carrito/{user_id}")
def get_cart(user_id: int):
    db = SessionLocal()
    items = db.query(Carrito).filter(Carrito.user_id == user_id).all()
    return [{"producto_id": i.producto_id} for i in items]

#* Comprar
@app.post("/comprar/")
def comprar(user_id: int):
    db = SessionLocal()
    items = db.query(Carrito).filter(Carrito.user_id == user_id).all()
    for item in items:
        compra = Compra(user_id=user_id, producto_id=item.producto_id)
        db.add(compra)
        db.delete(item)  # eliminar del carrito
    db.commit()
    return {"msg": "Compra realizada"}

@app.get("/compras/{user_id}")
def get_compras(user_id: int):
    db = SessionLocal()
    compras = db.query(Compra).filter(Compra.user_id == user_id).all()
    return [{"producto_id": c.producto_id, "fecha": c.fecha} for c in compras]
