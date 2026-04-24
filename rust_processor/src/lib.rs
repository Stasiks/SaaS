use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use image::{imageops::FilterType, ImageFormat, DynamicImage};
use std::io::Cursor;
use thiserror::Error;

// Кастомные ошибки через thiserror
#[derive(Error, Debug)]
pub enum ImageProcessingError {
    #[error("Failed to decode image: {0}")]
    DecodeError(#[from] image::ImageError),
    #[error("Failed to encode image")]
    EncodeError,
}

// Конвертация ошибки в исключение Python
impl From<ImageProcessingError> for PyErr {
    fn from(err: ImageProcessingError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}

/// Ядро логики на Rust
fn process_image_core(input_bytes: &[u8]) -> Result<Vec<u8>, ImageProcessingError> {
    // 1. Декодирование (Метаданные игнорируются)
    let img = image::load_from_memory(input_bytes)?;

    // 2. Нормализация (приведение к стандартному RGB8, удаление альфа-канала если есть)
    let rgb_img = img.into_rgb8();
    let dynamic_img = DynamicImage::ImageRgb8(rgb_img);

    // 3. Ресайз
    let resized = dynamic_img.resize_exact(1024, 1024, FilterType::Lanczos3);

    // 4. Кодирование обратно в байты (JPEG, качество 85)
    let mut result_bytes: Vec<u8> = Vec::new();
    resized.write_to(&mut Cursor::new(&mut result_bytes), ImageFormat::Jpeg)
        .map_err(|_| ImageProcessingError::EncodeError)?;

    Ok(result_bytes)
}

/// Python-обертка
#[pyfunction]
#[pyo3(signature = (input_bytes))]
fn process_image(input_bytes: &[u8]) -> PyResult<Vec<u8>> {
    let result = process_image_core(input_bytes)?;
    Ok(result)
}

/// Регистрация модуля для Python
#[pymodule]
fn rust_processor(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(process_image, m)?)?;
    Ok(())
}