from app.database import get_db

with get_db() as conn:
    c = conn.cursor()
    c.execute('DELETE FROM services')
    c.execute('DELETE FROM offers')
    c.execute('DELETE FROM gallery_images')
    c.execute('DELETE FROM categories')
    c.execute('DELETE FROM locations')
    c.execute('DELETE FROM salon_settings')
    c.execute('DELETE FROM availability_settings')
    c.execute('DELETE FROM admin_users')
    c.execute('DELETE FROM profiles')
    c.execute('DELETE FROM organizations')
    conn.commit()
    print('Database cleared')