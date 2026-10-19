
"""근골격계 종합 결과보고서: 본사 안전보건 업무지침서형 서식."""

import re
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

NAVY = "173D73"
LIGHT_BLUE = "E5EDF5"
LIGHT_GRAY = "F3F6F9"
BORDER = "C0CAD4"
TEXT = "222222"


def set_font(run, size, bold=None, color=TEXT):
    run.font.name = "맑은 고딕"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)

    if bold is not None:
        run.bold = bold

    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)

    for key in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn("w:" + key), "맑은 고딕")


def shade_cell(cell, color):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = tcpr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcpr.append(shd)
    shd.set(qn("w:fill"), color)


def style_borders(cell):
    tcpr = cell._tc.get_or_add_tcPr()
    borders = tcpr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcpr.append(borders)

    for side in ("top", "left", "bottom", "right"):
        edge = borders.find(qn("w:" + side))
        if edge is None:
            edge = OxmlElement("w:" + side)
            borders.append(edge)

        edge.set(qn("w:val"), "single")
        edge.set(qn("w:sz"), "4")
        edge.set(qn("w:color"), BORDER)


def heading_rule(paragraph):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = ppr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr")
        ppr.append(pbdr)

    bottom = pbdr.find(qn("w:bottom"))
    if bottom is None:
        bottom = OxmlElement("w:bottom")
        pbdr.append(bottom)

    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:color"), NAVY)
    bottom.set(qn("w:space"), "5")


def format_paragraph(paragraph, in_table=False, header=False):
    text = paragraph.text.strip()
    pf = paragraph.paragraph_format

    pf.space_before = Pt(0)
    pf.space_after = Pt(3 if not in_table else 1)
    pf.line_spacing = 1.22 if not in_table else 1.12

    size = 8.5 if in_table else 9
    bold = None
    color = TEXT

    # 실제 결과보고서의 번호형 제목을 인식
    main_heading = bool(
        not in_table
        and re.match(r"^\d+\.\s+\S+", text)
    )

    sub_heading = bool(
        not in_table
        and re.match(r"^\d+-\d+\.\s+\S+", text)
    )

    if main_heading:
        size = 11
        bold = True
        color = NAVY
        pf.space_before = Pt(12)
        pf.space_after = Pt(7)
        pf.keep_with_next = True
        heading_rule(paragraph)

    elif sub_heading:
        size = 10
        bold = True
        color = NAVY
        pf.space_before = Pt(8)
        pf.space_after = Pt(5)
        pf.keep_with_next = True

    elif not in_table and (
        "근골격계" in text
        and ("결과보고서" in text or "조사보고서" in text)
        and len(text) < 80
    ):
        size = 15
        bold = True
        color = NAVY
        pf.space_after = Pt(10)

    for run in paragraph.runs:
        set_font(
            run,
            size=size,
            bold=True if header or bold is True else None,
            color=NAVY if header else color
        )


def format_table(table):
    for row_idx, row in enumerate(table.rows):
        for col_idx, cell in enumerate(row.cells):
            cell.vertical_alignment = (
                WD_CELL_VERTICAL_ALIGNMENT.CENTER
            )

            style_borders(cell)

            if row_idx == 0:
                shade_cell(cell, LIGHT_BLUE)
            elif col_idx == 0 and len(row.cells) > 1:
                shade_cell(cell, LIGHT_GRAY)

            for paragraph in cell.paragraphs:
                format_paragraph(
                    paragraph,
                    in_table=True,
                    header=(row_idx == 0)
                )

            for nested in cell.tables:
                format_table(nested)



def apply_corporate_report_style_v2(document):
    """본사 업무지침서형 디자인: 기존 본문과 사진 유지."""
    import re
    from docx.shared import Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    navy = RGBColor(23, 61, 115)

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if not text:
            continue

        is_heading = bool(
            re.match(r"^\\d+\\.\\s+", text)
            or re.match(r"^\\d+-\\d+\\.\\s+", text)
        )

        if is_heading:
            paragraph.paragraph_format.space_before = Pt(12)
            paragraph.paragraph_format.space_after = Pt(7)
            paragraph.paragraph_format.keep_with_next = True

            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(11)
                run.font.color.rgb = navy

            ppr = paragraph._p.get_or_add_pPr()
            pbdr = ppr.find(qn("w:pBdr"))
            if pbdr is None:
                pbdr = OxmlElement("w:pBdr")
                ppr.append(pbdr)

            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "10")
            bottom.set(qn("w:color"), "173D73")
            bottom.set(qn("w:space"), "5")
            pbdr.append(bottom)

    for table in document.tables:
        if not table.rows:
            continue

        for cell in table.rows[0].cells:
            shade_cell(cell, "DCE8F4")

            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.bold = True
                    run.font.color.rgb = navy

    return document


def apply_corporate_report_style(document):
    """문서 내용, 사진, 계산값은 보존하고 서식만 적용."""

    for section in document.sections:
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.7)
        section.left_margin = Cm(1.8)
        section.right_margin = Cm(1.8)

    normal = document.styles["Normal"]
    normal.font.name = "맑은 고딕"
    normal.font.size = Pt(9)

    for paragraph in document.paragraphs:
        format_paragraph(paragraph)

    for table in document.tables:
        format_table(table)

    return final_report_cleanup_v4(finalize_corporate_report_v3(apply_corporate_report_style_v2(document)))


def finalize_corporate_report_v3(document):
    """종합보고서의 제목, 표, 사진 배치를 마무리한다."""
    import re
    from docx.shared import Pt, RGBColor, Cm
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    navy = RGBColor(23, 61, 115)
    dark = RGBColor(34, 34, 34)

    # 보고서에서 실제로 사용하는 주요 장 제목
    main_titles = (
        "조사 및 평가 개요",
        "근골격계 조사 결과 요약",
        "신체부위별 판정 현황",
        "부서별 근골격계 판정 현황",
        "근골격계 사후관리 대상자",
        "근골격계 종합 분석",
        "근골격계 향후 관리계획",
        "REBA 작업자세 평가 결과 요약",
        "공종별 REBA 평가 현황",
        "작업별 REBA 평가 현황",
        "REBA 고위험 작업 관리대상",
    )

    for p in document.paragraphs:
        text = p.text.strip()

        if not text:
            continue

        match = re.match(r"^(\\d{1,2})\\.\\s+(.+)$", text)

        is_main = (
            bool(match)
            and any(title in match.group(2) for title in main_titles)
        )

        is_sub = bool(
            re.match(r"^\\d{1,2}-\\d{1,2}\\.\\s+", text)
        )

        # 이전 스타일에서 모든 번호 문장을 제목으로
        # 취급했던 문제를 수정한다.
        if match and not is_main:
            ppr = p._p.get_or_add_pPr()
            border = ppr.find(qn("w:pBdr"))

            if border is not None:
                ppr.remove(border)

            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = False

            for run in p.runs:
                run.font.color.rgb = dark
                run.font.size = Pt(9)
                run.bold = False

        elif is_main:
            p.paragraph_format.space_before = Pt(11)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True

            for run in p.runs:
                run.font.color.rgb = navy
                run.font.size = Pt(11)
                run.bold = True

        elif is_sub:
            p.paragraph_format.space_before = Pt(7)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True

            for run in p.runs:
                run.font.color.rgb = navy
                run.font.size = Pt(10)
                run.bold = True

    # 표 행이 페이지 경계에서 반으로 분리되지 않게 한다.
    # 첫 번째 행은 다음 페이지에서도 머리글로 반복한다.
    def arrange_table(table):
        for row_index, row in enumerate(table.rows):
            trpr = row._tr.get_or_add_trPr()

            if trpr.find(qn("w:cantSplit")) is None:
                trpr.append(OxmlElement("w:cantSplit"))

            if row_index == 0:
                if trpr.find(qn("w:tblHeader")) is None:
                    head = OxmlElement("w:tblHeader")
                    head.set(qn("w:val"), "true")
                    trpr.append(head)

            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_before = Pt(1)
                    paragraph.paragraph_format.space_after = Pt(1)

                for nested in cell.tables:
                    arrange_table(nested)

    for table in document.tables:
        arrange_table(table)

    # 사진은 비율을 유지하며 너무 넓은 사진만 축소.
    # 사진의 순서와 원본 데이터는 변경하지 않는다.
    for shape in document.inline_shapes:
        if shape.width > Cm(17.0):
            ratio = Cm(17.0) / shape.width
            shape.width = Cm(17.0)
            shape.height = int(shape.height * ratio)

    # 첫 장의 조사 개요 표는 제목·항목명을 더 명확히 표시
    # 실제 조사 수치와 입력된 값은 변경하지 않는다.
    for table in document.tables[:1]:
        if not table.rows:
            continue

        for row in table.rows:
            if row.cells:
                first = row.cells[0]
                shade_cell(first, "E5EDF5")

                for p in first.paragraphs:
                    for run in p.runs:
                        run.bold = True
                        run.font.color.rgb = navy

    return document


def final_report_cleanup_v4(document):
    """기존 데이터와 사진을 보존하면서 Word 레이아웃 마무리."""
    import re
    from docx.shared import Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    navy = RGBColor(23, 61, 115)
    dark = RGBColor(34, 34, 34)

    # 실제 보고서의 장 제목만 남색으로 표시
    main_titles = {
        "조사 및 평가 개요",
        "근골격계 조사 결과 요약",
        "신체부위별 판정 현황",
        "부서별 근골격계 판정 현황",
        "근골격계 사후관리 대상자",
        "근골격계 종합 분석",
        "근골격계 향후 관리계획",
        "REBA 작업자세 평가 결과 요약",
        "공종별 REBA 평가 현황",
        "작업별 REBA 평가 현황",
        "REBA 고위험 작업 관리대상",
        "REBA 종합 분석",
        "REBA 향후 관리계획",
        "REBA 개선 전·후 비교 결과",
        "전체 개선조치 관리현황",
        "개선효과 종합 분석",
    }

    for p in document.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        match = re.match(
            r"^(\d{1,2})(?:\.)\s+(.+)$",
            text
        )

        is_main = bool(
            match
            and match.group(2).strip() in main_titles
        )

        # 11-1 등 소제목
        is_sub = bool(
            re.match(r"^\d{1,2}-\d{1,2}\.\s+", text)
        )

        # 제목이나 관리계획에 붙은 실제 Word 글머리표 제거
        if is_main or is_sub or match:
            ppr = p._p.get_or_add_pPr()
            numpr = ppr.find(qn("w:numPr"))

            if numpr is not None:
                ppr.remove(numpr)

        # 일반 번호 목록은 검은색 본문으로 처리
        if match and not is_main:
            ppr = p._p.get_or_add_pPr()
            border = ppr.find(qn("w:pBdr"))

            if border is not None:
                ppr.remove(border)

            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = False

            for run in p.runs:
                run.font.size = Pt(9)
                run.font.color.rgb = dark
                run.bold = False

        elif is_main:
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(6)

            for run in p.runs:
                run.font.size = Pt(11)
                run.font.color.rgb = navy
                run.bold = True

        elif is_sub:
            p.paragraph_format.keep_with_next = True

            for run in p.runs:
                run.font.size = Pt(10)
                run.font.color.rgb = navy
                run.bold = True

    # 표 한 행이 페이지 사이에서 잘리는 것 방지
    def fix_table(table):
        for row_index, row in enumerate(table.rows):
            trpr = row._tr.get_or_add_trPr()

            if trpr.find(qn("w:cantSplit")) is None:
                trpr.append(OxmlElement("w:cantSplit"))

            # 다음 페이지로 넘어갈 때 첫 행 반복
            if row_index == 0:
                if trpr.find(qn("w:tblHeader")) is None:
                    header = OxmlElement("w:tblHeader")
                    header.set(qn("w:val"), "true")
                    trpr.append(header)

            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(1)
                    p.paragraph_format.space_before = Pt(1)

                for nested in cell.tables:
                    fix_table(nested)

    for table in document.tables:
        fix_table(table)

    # 사진은 기존 크기와 비율 유지
    # 사진을 포함한 표 행만 페이지 중간 분리 방지
    # 사진의 데이터·경로·REBA 점수는 수정하지 않음

    return document
