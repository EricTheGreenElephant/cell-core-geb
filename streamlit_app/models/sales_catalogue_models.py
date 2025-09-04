# from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DECIMAL
# from sqlalchemy.orm import relationship
# from db.base import Base


# class SalesCatalogue(Base):
#     __tablename__ = "sales_catalogue"

#     id = Column(Integer, primary_key=True)
#     article_number = Column(Integer, unique=True, nullable=False)
#     package_name = Column(String(100), unique=True, nullable=False)
#     package_desc = Column(String(255), nullable=False)
#     price = Column(DECIMAL(10, 2), nullable=False)
#     is_active = Column(Boolean, default=True)

#     products = relationship("SalesCatalogueProduct", back_populates="catalogue")
#     supplements = relationship("SalesCatalogueSupplement", back_populates="catalogue")


# class SalesCatalogueProduct(Base):
#     __tablename__ = "sales_catalogue_products"

#     id = Column(Integer, primary_key=True)
#     catalogue_id = Column(Integer, ForeignKey("sales_catalogue.id"), nullable=False)
#     product_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
#     product_quantity = Column(Integer, nullable=False)

#     catalogue = relationship("SalesCatalogue", back_populates="products")


# class SalesCatalogueSupplement(Base):
#     __tablename__ = "sales_catalogue_supplements"

#     id = Column(Integer, primary_key=True)
#     catalogue_id = Column(Integer, ForeignKey("sales_catalogue.id"), nullable=False)
#     supplement_id = Column(Integer, ForeignKey("supplements.id"), nullable=False)
#     supplement_quantity = Column(Integer, nullable=False)

#     catalogue = relationship("SalesCatalogue", back_populates="supplements")
    