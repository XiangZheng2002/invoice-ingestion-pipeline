"""
文件处理服务
处理PDF、图片等文件
"""

import os
from PIL import Image
import tempfile

try:
    import pymupdf
except ImportError:  # pragma: no cover - 兼容旧版本PyMuPDF
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

class FileHandler:
    """文件处理类"""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()

    def pdf_to_images(self, pdf_path, dpi=200):
        """
        将PDF转换为图片（仅用于OCR兜底，电子发票应优先走文字层直接解析）

        使用PyMuPDF渲染，纯Python wheel自带渲染引擎，
        不像pdf2image那样依赖外部poppler二进制——打包分发时不会因缺依赖而失败。

        Args:
            pdf_path: PDF文件路径
            dpi: 渲染分辨率

        Returns:
            list: 图片路径列表
        """
        if pymupdf is None:
            print("PDF转图片失败: 未安装PyMuPDF")
            return []

        try:
            image_paths = []
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            zoom = dpi / 72.0

            with pymupdf.open(pdf_path) as doc:
                if doc.page_count == 0:
                    return []

                # 只渲染第一页（发票信息都在首页）
                page = doc[0]
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))

                image_path = os.path.join(self.temp_dir, f"{base_name}_page_1.jpg")
                pixmap.pil_save(image_path, format='JPEG', quality=95)
                image_paths.append(image_path)

            return image_paths

        except Exception as e:
            print(f"PDF转图片失败: {e}")
            return []

    def compress_image(self, image_path, max_size_kb=500):
        """
        压缩图片（如果需要）

        Args:
            image_path: 图片路径
            max_size_kb: 最大文件大小（KB）

        Returns:
            str: 压缩后的图片路径
        """
        try:
            # 检查文件大小
            file_size_kb = os.path.getsize(image_path) / 1024

            if file_size_kb <= max_size_kb:
                return image_path

            # 需要压缩
            image = Image.open(image_path)

            # 保持宽高比，缩小尺寸
            ratio = (max_size_kb * 1024 / os.path.getsize(image_path)) ** 0.5
            new_size = (int(image.width * ratio), int(image.height * ratio))

            image = image.resize(new_size, Image.Resampling.LANCZOS)

            # 保存压缩后的图片
            compressed_path = image_path.replace('.', '_compressed.')
            image.save(compressed_path, 'JPEG', quality=85, optimize=True)

            return compressed_path

        except Exception as e:
            print(f"图片压缩失败: {e}")
            return image_path

    def validate_file(self, file_path):
        """
        验证文件是否有效

        Args:
            file_path: 文件路径

        Returns:
            tuple: (是否有效, 文件类型, 错误信息)
        """
        if not os.path.exists(file_path):
            return False, None, '文件不存在'

        if not os.path.isfile(file_path):
            return False, None, '不是有效文件'

        # 检查文件大小（限制50MB）
        max_size = 50 * 1024 * 1024  # 50MB
        file_size = os.path.getsize(file_path)

        if file_size > max_size:
            return False, None, f'文件过大: {file_size / 1024 / 1024:.2f}MB (最大50MB)'

        # 检查文件类型
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            return True, 'pdf', None
        elif file_ext == '.ofd':
            return True, 'ofd', None
        elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff']:
            return True, 'image', None
        else:
            return False, None, f'不支持的文件类型: {file_ext}'

    def convert_to_jpg(self, image_path):
        """
        将图片转换为JPG格式

        Args:
            image_path: 图片路径

        Returns:
            str: JPG图片路径
        """
        try:
            file_ext = os.path.splitext(image_path)[1].lower()

            if file_ext == '.jpg' or file_ext == '.jpeg':
                return image_path

            # 打开图片
            image = Image.open(image_path)

            # 如果是PNG且有透明通道，需要转换
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background

            # 保存为JPG
            jpg_path = os.path.splitext(image_path)[0] + '.jpg'
            image.save(jpg_path, 'JPEG', quality=95)

            return jpg_path

        except Exception as e:
            print(f"图片格式转换失败: {e}")
            return image_path

    def clean_temp_files(self, file_paths):
        """
        清理临时文件

        Args:
            file_paths: 文件路径列表
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path) and self.temp_dir in file_path:
                    os.remove(file_path)
            except Exception as e:
                print(f"删除临时文件失败 {file_path}: {e}")

    def process_invoice_file(self, file_path):
        """
        处理发票文件，返回适合OCR的图片路径

        Args:
            file_path: 发票文件路径

        Returns:
            tuple: (success, image_path, error_message)
        """
        # 验证文件
        valid, file_type, error = self.validate_file(file_path)
        if not valid:
            return False, None, error

        try:
            if file_type == 'pdf':
                # PDF转图片
                image_paths = self.pdf_to_images(file_path)
                if not image_paths:
                    return False, None, 'PDF转图片失败'

                # 使用第一页
                image_path = image_paths[0]

            elif file_type == 'image':
                # 转换为JPG
                image_path = self.convert_to_jpg(file_path)

            elif file_type == 'ofd':
                # OFD无法渲染成图片，只能走文字层直接解析
                return False, None, 'OFD文件不支持OCR，请使用直接解析'

            else:
                return False, None, f'不支持的文件类型: {file_type}'

            # 压缩图片（OCR对文件大小有限制）
            final_path = self.compress_image(image_path, max_size_kb=2048)

            return True, final_path, None

        except Exception as e:
            return False, None, f'文件处理失败: {str(e)}'
