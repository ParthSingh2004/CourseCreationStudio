/**
 * slide_builder.js
 * ================
 * Builds a premium, well-structured PowerPoint presentation using PptxGenJS.
 *
 * Usage (called from Python via subprocess):
 *   node slide_builder.js <course_json_path> <output_pptx_path>
 *
 * Audio:
 *   PptxGenJS embeds MP3 files via addMedia(), which PowerPoint opens safely
 *   as click-to-play audio. Timing/autoplay XML is intentionally not injected
 *   by default because malformed timing blocks make PowerPoint repair the deck.
 */

import pptxgen from "pptxgenjs";
import fs from "node:fs";
import path from "node:path";
import JSZip from "jszip";

// ── Colour palette (no "#" prefix — PptxGenJS rule) ────────────────────────
const C = {
  BG_NAVY:    "0F1728",
  BG_CARD:    "13203A",
  BRAND_BLUE: "1E5EF3",
  ACCENT_DIM: "0A3AA8",
  ACCENT_TEAL:"38BDF8",
  WHITE:      "FFFFFF",
  MUTED:      "93C5FD",
  FAINT:      "64748B",
  TABLE_HDR:  "1E3A6E",
  TABLE_ODD:  "1A3058",
  TABLE_EVEN: "132242",
  TABLE_TEXT: "E2E8F0",
};

// ── Canvas (LAYOUT_WIDE = 13.3" × 7.5") ────────────────────────────────────
const W = 13.3;
const H = 7.5;

// ──────────────────────────────────────────────────────────────────────────
// SHARED CHROME
// ──────────────────────────────────────────────────────────────────────────

/** Header bar on every content slide: brand-blue band + teal bottom strip. */
function addHeaderBar(slide, label = "") {
  // Brand-blue header band (1.05" tall)
  slide.addShape(slide._pptx.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 1.05,
    fill: { color: C.BRAND_BLUE },
    line: { color: C.BRAND_BLUE },
  });

  // Teal bottom accent strip (thin)
  slide.addShape(slide._pptx.shapes.RECTANGLE, {
    x: 0, y: H - 0.07, w: W, h: 0.07,
    fill: { color: C.ACCENT_TEAL },
    line: { color: C.ACCENT_TEAL },
  });

  if (label) {
    slide.addText(label, {
      x: 11.5, y: 0.06, w: 1.65, h: 0.3,
      fontSize: 7.5, color: C.MUTED,
      align: "right", valign: "top",
      fontFace: "Arial",
    });
  }
}

/** White bold title sitting inside the header bar. */
function addSlideTitle(slide, title) {
  slide.addText(title, {
    x: 0.22, y: 0.17, w: 12.8, h: 0.75,
    fontSize: 22, color: C.WHITE, bold: true,
    align: "left", valign: "middle",
    fontFace: "Arial",
    margin: 0,
  });
}

/**
 * Bullet list in the content area.
 * Uses PptxGenJS bullet: true to avoid double-bullets.
 */
function addBullets(slide, bullets, opts = {}) {
  if (!bullets || bullets.length === 0) return;

  const {
    x = 0.38, y = 1.15, w = 12.5, h = 5.95,
    fontSize = 19,
  } = opts;

  const runs = bullets.map((b, i) => ({
    text: b,
    options: {
      bullet: true,
      fontSize,
      color: C.WHITE,
      fontFace: "Arial",
      breakLine: i < bullets.length - 1,
      paraSpaceAfter: 6,
      paraSpaceBefore: 6,
    },
  }));

  slide.addText(runs, {
    x, y, w, h,
    valign: "top",
    margin: [4, 8, 4, 8],
  });
}

// ──────────────────────────────────────────────────────────────────────────
// SPECIAL SLIDES
// ──────────────────────────────────────────────────────────────────────────

function buildCourseTitleSlide(prs, courseTitle, description) {
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  // Hero band (top ~2.7")
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 2.7,
    fill: { color: C.BRAND_BLUE },
    line: { color: C.BRAND_BLUE },
  });

  // Teal bottom strip
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: H - 0.28, w: W, h: 0.28,
    fill: { color: C.ACCENT_DIM },
    line: { color: C.ACCENT_DIM },
  });

  // Overline label
  slide.addText("C O U R S E   P R E S E N T A T I O N", {
    x: 0.45, y: 0.22, w: 10, h: 0.38,
    fontSize: 9, color: C.MUTED, bold: true,
    fontFace: "Arial", align: "left",
  });

  // Course title
  slide.addText(courseTitle, {
    x: 0.45, y: 2.85, w: 12.4, h: 2.0,
    fontSize: 38, color: C.WHITE, bold: true,
    fontFace: "Arial", align: "left",
  });

  // Teal divider rule
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0.45, y: 5.05, w: 4.5, h: 0.04,
    fill: { color: C.ACCENT_TEAL },
    line: { color: C.ACCENT_TEAL },
  });

  // Description
  slide.addText(description || "", {
    x: 0.45, y: 5.2, w: 12.0, h: 1.9,
    fontSize: 15, color: C.MUTED,
    fontFace: "Arial", align: "left",
  });

  return slide;
}

function buildModuleSectionSlide(prs, moduleIndex, moduleTitle) {
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  // Mid-band
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: 2.3, w: W, h: 3.0,
    fill: { color: C.BG_CARD },
    line: { color: C.BG_CARD },
  });

  // Bottom strip
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: H - 0.15, w: W, h: 0.15,
    fill: { color: C.BRAND_BLUE },
    line: { color: C.BRAND_BLUE },
  });

  // "MODULE X" overline
  slide.addText(`MODULE  ${moduleIndex}`, {
    x: 0.45, y: 2.48, w: 10, h: 0.5,
    fontSize: 13, color: C.ACCENT_TEAL, bold: true,
    fontFace: "Arial", align: "left",
  });

  // Module title
  slide.addText(moduleTitle, {
    x: 0.45, y: 3.0, w: 12.3, h: 1.75,
    fontSize: 32, color: C.WHITE, bold: true,
    fontFace: "Arial", align: "left",
  });

  return slide;
}

/**
 * Lesson-divider slide.
 * Audio is embedded here if provided.
 * Returns { slide, mediaShapeId } — mediaShapeId is needed for timing injection.
 */
function buildLessonHeaderSlide(prs, moduleIndex, lessonIndex, lessonTitle, audioPath) {
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  // Narrow top stripe
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: 0, w: W, h: 0.55,
    fill: { color: C.BRAND_BLUE },
    line: { color: C.BRAND_BLUE },
  });

  // Bottom strip
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0, y: H - 0.06, w: W, h: 0.06,
    fill: { color: C.ACCENT_TEAL },
    line: { color: C.ACCENT_TEAL },
  });

  // Overline
  slide.addText(`Module ${moduleIndex}  ·  Lesson ${lessonIndex}`, {
    x: 0.35, y: 0.1, w: 10, h: 0.38,
    fontSize: 9.5, color: C.MUTED,
    fontFace: "Arial", align: "left",
  });

  // Lesson title
  slide.addText(lessonTitle, {
    x: 0.45, y: 2.4, w: 12.0, h: 2.0,
    fontSize: 28, color: C.WHITE, bold: true,
    fontFace: "Arial", align: "left",
  });

  // Teal divider
  slide.addShape(prs.shapes.RECTANGLE, {
    x: 0.45, y: 4.55, w: 3.5, h: 0.04,
    fill: { color: C.ACCENT_TEAL },
    line: { color: C.ACCENT_TEAL },
  });

  let hasAudio = false;

  // Embed audio if the file exists
  if (audioPath && fs.existsSync(audioPath)) {
    try {
      // addMedia embeds the file and creates a clickable icon.
      // The icon is placed in a corner (tiny, unobtrusive).
      slide.addMedia({
        type:  "audio",
        path:  audioPath,
        x:     W - 0.55,
        y:     H - 0.55,
        w:     0.45,
        h:     0.45,
      });
      hasAudio = true;
      console.log(`[slide_builder]   ♪ Audio queued for embedding: ${path.basename(audioPath)}`);

      // Audio hint label
      slide.addText("▶  Click the audio icon to play narration", {
        x: 0.45, y: 5.1, w: 8, h: 0.38,
        fontSize: 9, color: C.ACCENT_TEAL,
        fontFace: "Arial", align: "left",
      });
    } catch (err) {
      console.error(`[slide_builder]   ✗ addMedia failed: ${err.message}`);
    }
  }

  return { slide, hasAudio };
}

// ──────────────────────────────────────────────────────────────────────────
// CONTENT SLIDES
// ──────────────────────────────────────────────────────────────────────────

function buildTextSlide(prs, segment, modIdx, lesIdx) {
  console.log(`[slide_builder]   → TEXT  '${segment.slide_title}'`);
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  addHeaderBar(slide, `M${modIdx}·L${lesIdx}·${segment.slide_index}`);
  addSlideTitle(slide, segment.slide_title || "");
  addBullets(slide, segment.slide_bullets || []);

  if (segment.narration) slide.addNotes(segment.narration);
  return slide;
}

function buildPhotoSlide(prs, segment, courseId, modIdx, lesIdx, imageDir) {
  console.log(`[slide_builder]   → PHOTO '${segment.slide_title}'`);
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  addHeaderBar(slide, `M${modIdx}·L${lesIdx}·${segment.slide_index}`);
  addSlideTitle(slide, segment.slide_title || "");

  let imgPath = null;
  if (segment.image_query && imageDir) {
    const candidate = path.join(imageDir, `${courseId}_${modIdx}_${lesIdx}_${segment.slide_index}.jpg`);
    if (fs.existsSync(candidate)) imgPath = candidate;
    else console.log(`[slide_builder]     ⚠ Image not found: ${candidate}`);
  }

  if (imgPath) {
    // Split layout: text left (~53%), image right (~44%)
    addBullets(slide, segment.slide_bullets || [], {
      x: 0.35, y: 1.15, w: 6.7, h: 5.9, fontSize: 17,
    });
    slide.addImage({
      path: imgPath,
      x: 7.25, y: 1.15, w: 5.75, h: 5.9,
    });
  } else {
    // Full-width bullets as fallback
    addBullets(slide, segment.slide_bullets || []);
  }

  if (segment.narration) slide.addNotes(segment.narration);
  return slide;
}

function buildTableSlide(prs, segment, modIdx, lesIdx) {
  console.log(`[slide_builder]   → TABLE '${segment.slide_title}'`);
  const slide = prs.addSlide();
  slide.background = { color: C.BG_NAVY };

  addHeaderBar(slide, `M${modIdx}·L${lesIdx}·${segment.slide_index}`);
  addSlideTitle(slide, segment.slide_title || "");

  const td = segment.table_data;
  if (!td || !td.headers || td.headers.length === 0) {
    console.log(`[slide_builder]     ⚠ No table_data — falling back to bullets.`);
    addBullets(slide, segment.slide_bullets || ["No table data available."]);
    if (segment.narration) slide.addNotes(segment.narration);
    return slide;
  }

  const headers = td.headers;
  const rows    = td.rows || [];

  // Build table rows array
  const tableData = [
    // Header row
    headers.map(h => ({
      text: h,
      options: {
        fill: { color: C.TABLE_HDR },
        color: C.WHITE,
        bold: true,
        align: "center",
        fontSize: 13,
        fontFace: "Arial",
      },
    })),
    // Data rows
    ...rows.map((row, ri) => {
      const bg = ri % 2 === 0 ? C.TABLE_ODD : C.TABLE_EVEN;
      return headers.map((_, ci) => ({
        text: String((row[ci] || "")).substring(0, 120),
        options: {
          fill: { color: bg },
          color: C.TABLE_TEXT,
          align: "left",
          fontSize: 12,
          fontFace: "Arial",
        },
      }));
    }),
  ];

  const rowCount = tableData.length;
  // Cap height so it never bleeds off slide
  const tableH   = Math.min(5.8, rowCount * 0.52);

  slide.addTable(tableData, {
    x: 0.38, y: 1.18,
    w: 12.6, h: tableH,
    border: { pt: 0.5, color: C.BG_NAVY },
  });

  if (segment.narration) slide.addNotes(segment.narration);
  return slide;
}

function routeSegment(prs, segment, courseId, modIdx, lesIdx, imageDir) {
  const type = (segment.slide_type || "text").trim().toLowerCase();
  if (type === "photo") return buildPhotoSlide(prs, segment, courseId, modIdx, lesIdx, imageDir);
  if (type === "table") return buildTableSlide(prs, segment, modIdx, lesIdx);
  return buildTextSlide(prs, segment, modIdx, lesIdx);
}

// ──────────────────────────────────────────────────────────────────────────
// AUTO-PLAY TIMING INJECTION (post-processing)
// ──────────────────────────────────────────────────────────────────────────

/**
 * Given a valid .pptx file on disk, for every slide that contains an
 * embedded audio <a:audioFile> or <p14:media> element, inject a
 * <p:timing> block that tells PowerPoint to auto-play it on slide entry.
 *
 * Strategy:
 *   1. Open the .pptx with JSZip.
 *   2. For each slide XML, check if it contains an audio media element.
 *   3. Find the shape id of the audio carrier (<p:pic> with audioFile).
 *   4. If no <p:timing> already present, inject the auto-play timing block.
 *   5. Write the modified .pptx back to disk.
 */
async function injectAutoPlayTiming(pptxPath) {
  console.log("[slide_builder] Injecting auto-play timing into:", path.basename(pptxPath));

  const buf  = fs.readFileSync(pptxPath);
  const zip  = await JSZip.loadAsync(buf);

  const slideFiles = Object.keys(zip.files).filter(
    name => /^ppt\/slides\/slide\d+\.xml$/.test(name)
  );

  let injectedCount = 0;

  for (const slideName of slideFiles) {
    const xmlStr = await zip.files[slideName].async("string");

    // Only process slides that contain embedded media (audio/video).
    // PptxGenJS addMedia() uses <a:videoFile> + <p14:media> for audio embeds.
    if (!xmlStr.includes("p14:media") && !xmlStr.includes("audioFile")) continue;

    // Check if timing already present
    if (xmlStr.includes("<p:timing>")) {
      console.log(`[slide_builder]   ⚠ ${slideName} already has <p:timing> — skipping.`);
      continue;
    }

    // Extract the shape id of the audio carrier pic element.
    // PptxGenJS creates:  <p:cNvPr id="N" name="Media ...">
    const idMatch = xmlStr.match(/<p:cNvPr\s+id="(\d+)"\s+name="Media/);
    if (!idMatch) {
      console.log(`[slide_builder]   ⚠ Could not find Media shape id in ${slideName} — skipping.`);
      continue;
    }
    const shapeId = idMatch[1];

    // Build auto-play timing XML.
    // Uses incrementing cTn ids starting at 1.
    const timingXml = [
      `<p:timing`,
      ` xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"`,
      ` xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">`,
      `<p:tnLst>`,
      `<p:par>`,
      `<p:cTn id="1" dur="indefinite" restart="whenNotActive" nodeType="tmRoot">`,
      `<p:childTnLst>`,
      `<p:seq concurrent="1" nextAc="seek">`,
      `<p:cTn id="2" dur="indefinite" nodeType="mainSeq">`,
      `<p:childTnLst>`,
      `<p:par>`,
      `<p:cTn id="3" fill="hold">`,
      `<p:stCondLst><p:cond delay="0"/></p:stCondLst>`,
      `<p:childTnLst>`,
      `<p:par>`,
      `<p:cTn id="4" fill="hold">`,
      `<p:stCondLst><p:cond delay="0"/></p:stCondLst>`,
      `<p:childTnLst>`,
      `<p:audio>`,
      `<p:cMediaNode vol="80000" mute="0" numSld="0" showWhenStopped="1">`,
      `<p:cTn id="5" fill="hold" display="0" masterRel="sameClick">`,
      `<p:stCondLst><p:cond delay="0"/></p:stCondLst>`,
      `</p:cTn>`,
      `<p:tgtEl><p:spTgt spid="${shapeId}"/></p:tgtEl>`,
      `</p:cMediaNode>`,
      `</p:audio>`,
      `</p:childTnLst>`,
      `</p:cTn>`,
      `</p:par>`,
      `</p:childTnLst>`,
      `</p:cTn>`,
      `</p:par>`,
      `</p:childTnLst>`,
      `</p:cTn>`,
      `<p:prevCondLst>`,
      `<p:cond evt="onPrevClick" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>`,
      `</p:prevCondLst>`,
      `<p:nextCondLst>`,
      `<p:cond evt="onNextClick" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond>`,
      `</p:nextCondLst>`,
      `</p:seq>`,
      `</p:childTnLst>`,
      `</p:cTn>`,
      `</p:par>`,
      `</p:tnLst>`,
      `<p:bldLst/>`,
      `</p:timing>`,
    ].join("");

    // Insert <p:timing> just before the closing </p:sld> tag
    const modifiedXml = xmlStr.replace("</p:sld>", timingXml + "</p:sld>");
    zip.file(slideName, modifiedXml);
    injectedCount++;
    console.log(`[slide_builder]   ✓ Timing injected into ${slideName} (shape id=${shapeId})`);
  }

  if (injectedCount > 0) {
    const outBuf = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
    fs.writeFileSync(pptxPath, outBuf);
    console.log(`[slide_builder] ✓ Auto-play timing injected into ${injectedCount} slide(s).`);
  } else {
    console.log("[slide_builder] No audio slides required timing injection.");
  }
}

// ──────────────────────────────────────────────────────────────────────────
// MAIN BUILD FUNCTION
// ──────────────────────────────────────────────────────────────────────────

async function buildSlides(course, outputPath, imageDir) {
  console.log(`\n[slide_builder] ═══ Building '${course.course_id}' ═══`);

  const prs = new pptxgen();
  // Store reference on prs so we can pass it to shape helpers via slide._pptx
  prs.layout = "LAYOUT_WIDE"; // 13.3" × 7.5"

  // Patch slides so helpers can access prs.shapes
  const origAddSlide = prs.addSlide.bind(prs);
  prs.addSlide = function(...args) {
    const s = origAddSlide(...args);
    s._pptx = prs;
    return s;
  };

  // ── Audio lookup ───────────────────────────────────────────────────────
  const audioLookup = {};
  if (course.audio && Array.isArray(course.audio)) {
    for (const la of course.audio) {
      audioLookup[la.lesson_id] = la.audio_file;
    }
    console.log(`[slide_builder] Audio available for ${Object.keys(audioLookup).length} lesson(s).`);
  }

  let hasAnyAudio = false;

  // ── Cover slide ────────────────────────────────────────────────────────
  buildCourseTitleSlide(prs, course.outline.title, course.outline.description || "");

  // ── Modules ────────────────────────────────────────────────────────────
  for (const module of (course.outline.modules || [])) {
    console.log(`[slide_builder] Module ${module.index}: ${module.title}`);
    buildModuleSectionSlide(prs, module.index, module.title);

    if (!course.content) continue;

    const moduleLessons = (course.content.lessons || []).filter(
      l => l.module_index === module.index
    );
    console.log(`[slide_builder]   ${moduleLessons.length} lesson(s).`);

    for (const lesson of moduleLessons) {
      const lessonId  = `${course.course_id}_m${module.index}_l${lesson.lesson_index}`;
      const audioPath = audioLookup[lessonId] || null;

      console.log(`[slide_builder]   Lesson ${lesson.lesson_index}: '${lesson.title}' (${(lesson.segments||[]).length} segments)`);
      if (audioPath) console.log(`[slide_builder]   ♪ Audio: ${path.basename(audioPath)}`);

      const { hasAudio } = buildLessonHeaderSlide(
        prs, module.index, lesson.lesson_index, lesson.title, audioPath
      );
      if (hasAudio) hasAnyAudio = true;

      for (const segment of (lesson.segments || [])) {
        try {
          routeSegment(prs, segment, course.course_id, module.index, lesson.lesson_index, imageDir);
        } catch (err) {
          console.error(`[slide_builder]   ✗ Segment ${segment.slide_index} error: ${err.message}`);
        }
      }
    }
  }

  // ── Write file ─────────────────────────────────────────────────────────
  await prs.writeFile({ fileName: outputPath });
  console.log(`[slide_builder] ✓ Written: ${outputPath}`);

  // ── Optional experimental auto-play timing ─────────────────────────────
  // This is disabled by default because custom timing XML can make PowerPoint
  // show "found a problem with content" repair prompts.
  if (hasAnyAudio && process.env.PPTX_ENABLE_AUDIO_AUTOPLAY === "1") {
    await injectAutoPlayTiming(outputPath);
  } else if (hasAnyAudio) {
    console.log("[slide_builder] Audio embedded without timing injection (repair-safe).");
  }

  return outputPath;
}

// ──────────────────────────────────────────────────────────────────────────
// CLI ENTRY POINT
// ──────────────────────────────────────────────────────────────────────────

async function main() {
  const [,, courseJsonPath, outputPptxPath, imageDir] = process.argv;

  if (!courseJsonPath || !outputPptxPath) {
    console.error("Usage: node slide_builder.js <course.json> <output.pptx> [imageDir]");
    process.exit(1);
  }

  if (!fs.existsSync(courseJsonPath)) {
    console.error(`Course JSON not found: ${courseJsonPath}`);
    process.exit(1);
  }

  const course = JSON.parse(fs.readFileSync(courseJsonPath, "utf8"));
  await buildSlides(course, outputPptxPath, imageDir || null);
}

main().catch(err => {
  console.error("[slide_builder] FATAL:", err);
  process.exit(1);
});
