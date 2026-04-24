import io
import time
import random
from PIL import Image
import rust_processor

def generate_test_image_bytes(resolution: int) -> bytes:
    """Генерирует JPEG изображение заданного разрешения в памяти."""
    img = Image.new('RGB', (resolution, resolution), color=(
        random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
    ))
    pixels = img.load()
    for i in range(0, resolution, 10):
        for j in range(0, resolution, 10):
            pixels[i, j] = (0, 0, 0)
            
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    return buf.getvalue()

def process_with_pillow(input_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(input_bytes)) as img:
        # Нормализация
        if img.mode != 'RGB':
            img = img.convert('RGB')
        # Удаление метаданных 
        data = list(img.getdata())
        image_without_exif = Image.new(img.mode, img.size)
        image_without_exif.putdata(data)
        # Ресайз
        resized = image_without_exif.resize((1024, 1024), Image.Resampling.LANCZOS)
        
        out_buf = io.BytesIO()
        resized.save(out_buf, format='JPEG', quality=85)
        return out_buf.getvalue()

def run_benchmark():
    # Разрешения для симуляции разных размеров файлов
    resolutions = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
    
    print("| File Size | Python (Pillow) Time | Rust (image) Time | Speedup X |")
    print("|-----------|----------------------|-------------------|-----------|")
    
    for res in resolutions:
        img_bytes = generate_test_image_bytes(res)
        file_size_mb = len(img_bytes) / (1024 * 1024)
        
        # Benchmark Pillow
        start_py = time.perf_counter()
        process_with_pillow(img_bytes)
        time_py = time.perf_counter() - start_py
        
        # Benchmark Rust
        start_rs = time.perf_counter()
        rust_processor.process_image(img_bytes)
        time_rs = time.perf_counter() - start_rs
        
        speedup = time_py / time_rs if time_rs > 0 else 0
        
        print(f"| {file_size_mb:.2f} MB | {time_py:.4f} s | {time_rs:.4f} s | **{speedup:.2f}x** |")

if __name__ == "__main__":
    run_benchmark()