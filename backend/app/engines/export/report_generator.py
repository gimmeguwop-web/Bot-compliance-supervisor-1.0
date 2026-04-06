"""
Export module for generating validation reports in DOCX and XLSX formats.
"""
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
from docx import Document as DocxDocument
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
import pandas as pd
from app.core.logger import logger


class ReportGenerator:
    """Generate validation reports in DOCX and XLSX formats."""
    
    def __init__(self, output_dir: str = "/app/data/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_docx_report(
        self, 
        document_name: str,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate a structured DOCX report with violations, warnings, and recommendations.
        
        Args:
            document_name: Name of the validated document
            results: List of validation results
            metadata: Document metadata (task_id, timestamp, profile, etc.)
            
        Returns:
            Path to the generated DOCX file
        """
        doc = DocxDocument()
        
        # Title
        title = doc.add_heading(f"Отчёт проверки: {document_name}", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Metadata section
        doc.add_heading("Общая информация", level=1)
        meta_table = doc.add_table(rows=4, cols=2)
        meta_table.style = 'Table Grid'
        
        meta_data = [
            ("Дата проверки", metadata.get('timestamp', datetime.now()).strftime("%Y-%m-%d %H:%M:%S")),
            ("Профиль ЕСКД", metadata.get('profile', 'Не указан')),
            ("Статус", "Завершено"),
            ("Всего проверок", str(len(results)))
        ]
        
        for idx, (label, value) in enumerate(meta_data):
            meta_table.cell(idx, 0).text = label
            meta_table.cell(idx, 1).text = value
        
        # Summary statistics
        errors = sum(1 for r in results if r.get('status') == 'error')
        warnings = sum(1 for r in results if r.get('status') == 'warning')
        passed = sum(1 for r in results if r.get('status') == 'pass')
        
        doc.add_heading("Статистика", level=1)
        stats_table = doc.add_table(rows=3, cols=2)
        stats_table.style = 'Table Grid'
        
        stats_data = [
            ("✅ Прошло", str(passed)),
            ("⚠️ Предупреждения", str(warnings)),
            ("❌ Ошибки", str(errors))
        ]
        
        for idx, (label, value) in enumerate(stats_data):
            stats_table.cell(idx, 0).text = label
            stats_table.cell(idx, 1).text = value
        
        # Detailed results
        doc.add_heading("Детализация проверок", level=1)
        
        for result in results:
            status_icon = {"error": "❌", "warning": "⚠️", "pass": "✅"}.get(result.get('status', ''), '•')
            
            heading = f"{status_icon} {result.get('rule_id', 'Unknown Rule')}"
            para = doc.add_heading(heading, level=2)
            
            # Color code based on status
            if result.get('status') == 'error':
                para.runs[0].font.color.rgb = None  # Default to red in styling
            
            doc.add_paragraph(f"**Описание:** {result.get('description', 'Нет описания')}")
            
            if result.get('details'):
                doc.add_paragraph(f"**Детали:** {result.get('details')}")
            
            if result.get('page_ref'):
                doc.add_paragraph(f"**Страница:** {result.get('page_ref')}")
            
            if result.get('gost_link'):
                doc.add_paragraph(f"**ГОСТ:** {result.get('gost_link')}")
            
            if result.get('recommendation'):
                rec_para = doc.add_paragraph(f"**Рекомендация:** {result.get('recommendation')}")
                rec_para.style = 'Intense Quote'
            
            doc.add_paragraph()  # Spacer
        
        # Footer
        doc.add_page_break()
        footer = doc.add_paragraph("Сгенерировано автоматически системой проверки ЕСКД/ГОСТ")
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.style = 'Intense Quote'
        
        # Save
        filename = f"report_{metadata.get('task_id', 'unknown')}_{document_name.replace(' ', '_')}.docx"
        filepath = self.output_dir / filename
        doc.save(str(filepath))
        
        logger.info(f"DOCX report generated: {filepath}")
        return str(filepath)
    
    def generate_xlsx_report(
        self,
        document_name: str,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Generate a machine-readable XLSX matrix report.
        
        Args:
            document_name: Name of the validated document
            results: List of validation results
            metadata: Document metadata
            
        Returns:
            Path to the generated XLSX file
        """
        # Prepare data for DataFrame
        rows = []
        for result in results:
            row = {
                'Файл': document_name,
                'Task ID': metadata.get('task_id', ''),
                'Правило ID': result.get('rule_id', ''),
                'Описание': result.get('description', ''),
                'Статус': result.get('status', 'unknown'),
                'Страница': result.get('page_ref', ''),
                'Детали': result.get('details', ''),
                'ГОСТ ссылка': result.get('gost_link', ''),
                'Рекомендация': result.get('recommendation', ''),
                'Уверенность': result.get('confidence', ''),
                'Тип проверки': result.get('check_type', '')
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save to Excel with formatting
        filename = f"matrix_report_{metadata.get('task_id', 'unknown')}_{document_name.replace(' ', '_')}.xlsx"
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(str(filepath), engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Результаты', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Результаты']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        logger.info(f"XLSX report generated: {filepath}")
        return str(filepath)
    
    def generate_reports(
        self,
        document_name: str,
        results: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate both DOCX and XLSX reports.
        
        Returns:
            Dictionary with paths to generated files
        """
        docx_path = self.generate_docx_report(document_name, results, metadata)
        xlsx_path = self.generate_xlsx_report(document_name, results, metadata)
        
        return {
            "docx": docx_path,
            "xlsx": xlsx_path
        }


__all__ = ["ReportGenerator"]
