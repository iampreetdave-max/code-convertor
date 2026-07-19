/* =========================================================================
   CodeTransform — Converter page logic
   -------------------------------------------------------------------------
   This file is the ORIGINAL converter script, unchanged, moved out of
   index.html's inline <script> tag into its own file. Every function,
   element ID, and fetch() call below is identical to the original so the
   FastAPI backend keeps working exactly as before with no backend changes.
   Endpoints used (unchanged): POST /detect-language, POST /convert,
   POST /validate.
   ========================================================================= */

    // File extension to language mapping
    const extensionToLanguage = {
      'py': 'python',
      'js': 'javascript',
      'ts': 'typescript',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'cpp',
      'cs': 'csharp',
      'go': 'go',
      'rs': 'rust',
      'rb': 'ruby',
      'php': 'php'
    };

    // Prism language mapping
    const languageToPrism = {
      'python': 'python',
      'javascript': 'javascript',
      'typescript': 'typescript',
      'java': 'java',
      'cpp': 'cpp',
      'csharp': 'csharp',
      'go': 'go',
      'rust': 'rust',
      'ruby': 'ruby',
      'php': 'php'
    };

    // Language to file extension mapping
    const languageToExtension = {
      'python': 'py',
      'javascript': 'js',
      'typescript': 'ts',
      'java': 'java',
      'cpp': 'cpp',
      'csharp': 'cs',
      'go': 'go',
      'rust': 'rs',
      'ruby': 'rb',
      'php': 'php'
    };

    // Language display names
    const languageNames = {
      'python': 'Python',
      'javascript': 'JavaScript',
      'typescript': 'TypeScript',
      'java': 'Java',
      'cpp': 'C++',
      'csharp': 'C#',
      'go': 'Go',
      'rust': 'Rust',
      'ruby': 'Ruby',
      'php': 'PHP'
    };

    // Stats tracking
    let stats = JSON.parse(localStorage.getItem('codeTransformStats') || '{"conversions": 0, "totalTime": 0, "successes": 0}');
    let history = JSON.parse(localStorage.getItem('codeTransformHistory') || '[]');
    let lastConversionData = null;

    // Initialize
    document.addEventListener('DOMContentLoaded', () => {
      updateStats();
      renderHistory();
      setupDropZone();
      setupLineCounters();
      setupKeyboardShortcuts();
      setupLanguageBadges();
      setupSyntaxHighlighting();
    });

    // Auto-detection debounce
    let detectionTimeout;

    // Syntax highlighting functions
    function setupSyntaxHighlighting() {
      const sourceCode = document.getElementById('sourceCode');
      const outputCode = document.getElementById('outputCode');
      const sourceHighlight = document.getElementById('sourceHighlight');
      const outputHighlight = document.getElementById('outputHighlight');

      // Update highlighting on input and trigger auto-detection
      sourceCode.addEventListener('input', () => {
        updateSourceHighlight();

        // Auto-detect language with debouncing
        clearTimeout(detectionTimeout);
        if (sourceCode.value.trim() && !document.getElementById('fromLanguage').value) {
          detectionTimeout = setTimeout(() => {
            autoDetectLanguage();
          }, 500);
        } else if (!sourceCode.value.trim()) {
          document.getElementById('detectedLanguageDisplay').classList.add('hidden');
        }
      });

      // Sync scroll between textarea and highlight layer
      sourceCode.addEventListener('scroll', () => {
        sourceHighlight.scrollTop = sourceCode.scrollTop;
        sourceHighlight.scrollLeft = sourceCode.scrollLeft;
      });
      outputCode.addEventListener('scroll', () => {
        outputHighlight.scrollTop = outputCode.scrollTop;
        outputHighlight.scrollLeft = outputCode.scrollLeft;
      });

      // Update language on selection change
      document.getElementById('fromLanguage').addEventListener('change', () => {
        updateSourceHighlight();
        document.getElementById('detectedLanguageDisplay').classList.add('hidden');
      });
      document.getElementById('toLanguage').addEventListener('change', updateOutputHighlight);
    }

    // Auto-detect language function
    async function autoDetectLanguage() {
      const code = document.getElementById('sourceCode').value;
      if (!code.trim()) return;

      try {
        const response = await fetch('https://onrender.com', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code })
        });

        const data = await response.json();
        if (data.detected_language && data.detected_language !== 'unknown') {
          // Show detected language without auto-filling
          const displayName = languageNames[data.detected_language] || data.detected_language;
          const aiTag = data.reason && data.reason.startsWith('[AI]') ? ' (AI)' : '';
          document.getElementById('detectedLanguageName').textContent = displayName + aiTag;
          document.getElementById('detectedLanguageDisplay').classList.remove('hidden');
        }
      } catch (error) {
        console.error('Error auto-detecting language:', error);
      }
    }

    function updateSourceHighlight() {
      const code = document.getElementById('sourceCode').value;
      const lang = document.getElementById('fromLanguage').value || 'python';
      const prismLang = languageToPrism[lang] || 'javascript';
      const codeEl = document.getElementById('sourceCodeHighlight');

      // Update language class
      codeEl.className = `language-${prismLang}`;

      // Set text and highlight
      codeEl.textContent = code || ' ';
      Prism.highlightElement(codeEl);
    }

    function updateOutputHighlight() {
      const code = document.getElementById('outputCode').value;
      const lang = document.getElementById('toLanguage').value || 'javascript';
      const prismLang = languageToPrism[lang] || 'javascript';
      const codeEl = document.getElementById('outputCodeHighlight');

      // Update language class
      codeEl.className = `language-${prismLang}`;

      // Set text and highlight
      codeEl.textContent = code || ' ';
      Prism.highlightElement(codeEl);
    }

    // Diff view functions
    function renderDiffView(sourceCode, convertedCode) {
      const diffContent = document.getElementById('diffContent');
      const diffStats = document.getElementById('diffStats');

      if (!sourceCode || !convertedCode) {
        diffContent.innerHTML = '<p class="text-sm text-neutral-500 text-center py-8">Diff will appear after conversion</p>';
        diffStats.classList.add('hidden');
        return;
      }

      // Use jsdiff to compute line differences
      const diff = Diff.diffLines(sourceCode, convertedCode);

      let html = '';
      let lineNum = 1;
      let addedCount = 0;
      let removedCount = 0;
      let unchangedCount = 0;

      diff.forEach(part => {
        const lines = part.value.split('\n');
        // Remove last empty element if exists
        if (lines[lines.length - 1] === '') lines.pop();

        lines.forEach(line => {
          let className = 'diff-unchanged';
          let prefix = ' ';

          if (part.added) {
            className = 'diff-added';
            prefix = '+';
            addedCount++;
          } else if (part.removed) {
            className = 'diff-removed';
            prefix = '-';
            removedCount++;
          } else {
            unchangedCount++;
          }

          const escapedLine = escapeHtml(line) || '&nbsp;';
          html += `<div class="diff-line ${className}">
            <span class="diff-line-number">${lineNum}</span>
            <span class="diff-line-content">${prefix} ${escapedLine}</span>
          </div>`;
          lineNum++;
        });
      });

      diffContent.innerHTML = html;

      // Update stats
      document.getElementById('diffAdded').textContent = addedCount;
      document.getElementById('diffRemoved').textContent = removedCount;
      document.getElementById('diffUnchanged').textContent = unchangedCount;
      diffStats.classList.remove('hidden');
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    // Language badges
    function setupLanguageBadges() {
      document.getElementById('fromLanguage').addEventListener('change', updateSourceBadge);
      document.getElementById('toLanguage').addEventListener('change', updateTargetBadge);
    }

    function updateSourceBadge() {
      const lang = document.getElementById('fromLanguage').value;
      const badge = document.getElementById('sourceLanguageBadge');
      if (lang && languageNames[lang]) {
        badge.textContent = languageNames[lang];
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }

    function updateTargetBadge() {
      const lang = document.getElementById('toLanguage').value;
      const badge = document.getElementById('targetLanguageBadge');
      if (lang && languageNames[lang]) {
        badge.textContent = languageNames[lang];
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    }

    // Toast notifications
    function showToast(message, type = 'success') {
      const container = document.getElementById('toastContainer');
      const toast = document.createElement('div');
      const bgColor = type === 'success' ? 'bg-neutral-700' : type === 'error' ? 'bg-neutral-600' : 'bg-neutral-800';
      toast.className = `toast ${bgColor} px-4 py-2 rounded-lg text-sm shadow-lg border border-neutral-600`;
      toast.textContent = message;
      container.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    }

    // File upload handling
    function setupDropZone() {
      const dropZone = document.getElementById('dropZone');
      const fileInput = document.getElementById('fileInput');

      dropZone.addEventListener('click', (e) => {
        e.preventDefault();
        fileInput.click();
      });

      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      });

      dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
      });

      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleFile(file);
      });

      fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleFile(file);
      });
    }

    function handleFile(file) {
      const extension = file.name.split('.').pop().toLowerCase();
      const language = extensionToLanguage[extension];

      const reader = new FileReader();
      reader.onload = (e) => {
        document.getElementById('sourceCode').value = e.target.result;
        if (language) {
          document.getElementById('fromLanguage').value = language;
          updateSourceBadge();
          showToast(`Detected ${languageNames[language] || language} from file extension`);
        }
        updateSourceLineCount();
        updateSourceHighlight();
      };
      reader.readAsText(file);
    }

    // Line counters
    function setupLineCounters() {
      const sourceCode = document.getElementById('sourceCode');
      sourceCode.addEventListener('input', updateSourceLineCount);
    }

    function updateSourceLineCount() {
      const code = document.getElementById('sourceCode').value;
      const lines = code ? code.split('\n').length : 0;
      document.getElementById('sourceLineCount').textContent = `${lines} line${lines !== 1 ? 's' : ''}`;
    }

    function updateOutputLineCount() {
      const code = document.getElementById('outputCode').value;
      const lines = code ? code.split('\n').length : 0;
      document.getElementById('outputLineCount').textContent = `${lines} line${lines !== 1 ? 's' : ''}`;
    }

    // Keyboard shortcuts
    function setupKeyboardShortcuts() {
      document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
          e.preventDefault();
          convertCode();
        }
        if (e.ctrlKey && e.key === 's') {
          e.preventDefault();
          downloadCode();
        }
      });
    }

    // Language detection
    async function detectLanguage() {
      const code = document.getElementById("sourceCode").value;
      if (!code.trim()) return null;

      try {
        const response = await fetch('https://onrender.com', {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ code })
        });

        const data = await response.json();
        if (data.detected_language !== "unknown") {
          document.getElementById("fromLanguage").value = data.detected_language;
          updateSourceBadge();
          return data;
        }
        return null;
      } catch (error) {
        console.error("Error detecting language:", error);
        return null;
      }
    }

    // Code conversion
    async function convertCode() {
      const code = document.getElementById("sourceCode").value;
      let source = document.getElementById("fromLanguage").value;
      const target = document.getElementById("toLanguage").value;

      if (!code.trim()) {
        showToast("Please enter some code", "error");
        return;
      }

      if (!target) {
        showToast("Please select a target language", "error");
        return;
      }

      // Auto-detect if not selected
      if (!source) {
        await detectLanguage();
        source = document.getElementById("fromLanguage").value;
        if (!source) {
          showToast("Could not detect source language. Please select manually.", "error");
          return;
        }
      }

      const convertBtn = document.getElementById('convertBtn');
      convertBtn.classList.add('converting');
      convertBtn.disabled = true;

      const startTime = performance.now();

      try {
        const response = await fetch('https://onrender.com', {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code,
            source_language: source,
            target_language: target
          })
        });

        const data = await response.json();
        const endTime = performance.now();
        const conversionTime = ((endTime - startTime) / 1000).toFixed(2);

        // Store conversion time in data for report
        data._conversionTime = conversionTime;
        lastConversionData = data;

        document.getElementById("outputCode").value = data.converted_code;
        updateOutputLineCount();
        updateTargetBadge();
        updateOutputHighlight();

        // Update stats
        stats.conversions++;
        stats.totalTime += parseFloat(conversionTime);
        if (data.conversion_confidence >= 0.6) stats.successes++;
        localStorage.setItem('codeTransformStats', JSON.stringify(stats));
        updateStats();

        // Add to history
        addToHistory(code, data.converted_code, source, target, data.conversion_confidence);

        // Render comprehensive report
        renderConversionReport(data, source, target);

        // Render diff view
        renderDiffView(code, data.converted_code);

        showToast(`Converted in ${conversionTime}s`);

        // Run AI validation in background
        runValidation(code, data.converted_code, target);
      } catch (error) {
        console.error("Error converting code:", error);
        showToast("Error converting code. Check if backend is running.", "error");
      } finally {
        convertBtn.classList.remove('converting');
        convertBtn.disabled = false;
      }
    }

    // AI Validation
    async function runValidation(originalCode, convertedCode, targetLanguage) {
      const section = document.getElementById('validationSection');
      const content = document.getElementById('validationContent');
      const status = document.getElementById('validationStatus');

      // Show section with loading state
      section.classList.remove('hidden');
      status.textContent = 'Validating...';
      content.innerHTML = '<p class="text-sm text-neutral-500 text-center py-4">Running AI validation...</p>';

      try {
        const response = await fetch('https://onrender.com', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            converted_code: convertedCode,
            original_code: originalCode,
            target_language: targetLanguage
          })
        });

        if (!response.ok) {
          throw new Error(`Validation failed: ${response.status}`);
        }

        const data = await response.json();
        renderValidationResults(data);
      } catch (error) {
        console.error('Validation error:', error);
        status.textContent = 'Failed';
        content.innerHTML = `<p class="text-sm text-neutral-500 text-center py-4">Validation unavailable: ${error.message}</p>`;
      }
    }

    function renderValidationResults(data) {
      const content = document.getElementById('validationContent');
      const status = document.getElementById('validationStatus');

      const score = data.score || 0;
      const scorePercent = (score / 10) * 100;
      status.textContent = `Score: ${score}/10`;

      let compilationBadge = '';
      if (data.compilation_check === 'PASS') {
        compilationBadge = '<span class="px-2 py-0.5 bg-neutral-800 text-neutral-300 rounded text-xs border border-neutral-700">COMPILE: PASS</span>';
      } else if (data.compilation_check === 'FAIL') {
        compilationBadge = '<span class="px-2 py-0.5 bg-neutral-800 text-neutral-500 rounded text-xs border border-neutral-700">COMPILE: FAIL</span>';
      }

      let issuesHtml = '';
      if (data.issues && data.issues.length > 0) {
        issuesHtml = `
          <div class="mt-4">
            <p class="text-xs font-semibold text-neutral-400 mb-2">Issues Found:</p>
            <ul class="space-y-1">
              ${data.issues.map(issue => `
                <li class="text-xs text-neutral-400 flex items-start gap-2">
                  <span class="text-neutral-600 mt-0.5">&#x2022;</span>
                  <span>${escapeHtml(issue)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        `;
      }

      let suggestionsHtml = '';
      if (data.suggestions && data.suggestions.length > 0) {
        suggestionsHtml = `
          <div class="mt-4">
            <p class="text-xs font-semibold text-neutral-400 mb-2">Suggestions:</p>
            <ul class="space-y-1">
              ${data.suggestions.map(s => `
                <li class="text-xs text-neutral-400 flex items-start gap-2">
                  <span class="text-neutral-500 mt-0.5">-></span>
                  <span>${escapeHtml(s)}</span>
                </li>
              `).join('')}
            </ul>
          </div>
        `;
      }

      content.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-3">
            <span class="text-2xl font-bold text-white">${score}/10</span>
            ${compilationBadge}
          </div>
          <span class="text-xs ${data.is_valid ? 'text-neutral-300' : 'text-neutral-500'}">${data.is_valid ? 'Valid' : 'Issues Found'}</span>
        </div>
        <div class="validation-score-bar mb-4">
          <div class="validation-score-fill" style="width: ${scorePercent}%; opacity: ${0.3 + (scorePercent / 100) * 0.7}"></div>
        </div>
        <p class="text-sm text-neutral-400">${escapeHtml(data.feedback || '')}</p>
        ${issuesHtml}
        ${suggestionsHtml}
      `;
    }

    // Render comprehensive conversion report
    function renderConversionReport(data, source, target) {
      const report = document.getElementById('conversionReport');
      report.classList.remove('hidden');

      // Timestamp
      document.getElementById('reportTimestamp').textContent = new Date().toLocaleString();

      // Calculate confidence percentage
      const confidence = data.conversion_confidence || 0;
      const confidencePercent = (confidence * 100).toFixed(1);

      // Update circular progress
      const ring = document.getElementById('confidenceRing');
      const circumference = 2 * Math.PI * 56; // r=56
      const offset = circumference - (confidence * circumference);
      ring.style.strokeDashoffset = offset;

      // Update confidence display
      document.getElementById('confidencePercent').textContent = `${confidencePercent}%`;

      // Monochrome labels based on confidence level
      const confidenceCard = document.getElementById('confidenceCard');
      const percentEl = document.getElementById('confidencePercent');
      const labelEl = document.getElementById('confidenceLabel');
      const hintEl = document.getElementById('confidenceHint');

      if (confidence >= 0.85) {
        ring.className = 'confidence-ring text-white';
        percentEl.className = 'text-3xl font-bold text-white';
        labelEl.textContent = 'High Confidence';
        labelEl.className = 'text-sm text-neutral-300 font-medium';
        hintEl.textContent = 'Conversion completed successfully with minimal modifications needed.';
        confidenceCard.classList.remove('warning-state');
      } else if (confidence >= 0.65) {
        ring.className = 'confidence-ring text-neutral-400';
        percentEl.className = 'text-3xl font-bold text-neutral-300';
        labelEl.textContent = 'Review Recommended';
        labelEl.className = 'text-sm text-neutral-400 font-medium';
        hintEl.textContent = 'Some constructs may require manual verification.';
        confidenceCard.classList.remove('warning-state');
      } else {
        ring.className = 'confidence-ring text-neutral-600';
        percentEl.className = 'text-3xl font-bold text-neutral-500';
        labelEl.textContent = 'Manual Review Required';
        labelEl.className = 'text-sm text-neutral-500 font-medium';
        hintEl.textContent = 'Significant portions may need manual adjustment.';
        confidenceCard.classList.add('warning-state');
      }

      // Confidence breakdown (derived from metadata)
      const metadata = data.metadata || {};
      const linesProcessed = metadata.lines_processed || 0;
      const blocksDetected = metadata.blocks_detected || 0;

      // Derive scores from available data
      const structureScore = Math.min(100, confidence * 100 + (blocksDetected > 0 ? 10 : 0));
      const syntaxScore = confidence >= 0.6 ? Math.min(100, confidence * 100 + 5) : confidence * 100;
      const completenessScore = linesProcessed > 0 ? Math.min(100, (1 - (data.unsupported_lines_count || 0) / linesProcessed) * 100) : confidence * 100;

      document.getElementById('structureScore').textContent = `${structureScore.toFixed(0)}%`;
      document.getElementById('structureBar').style.width = `${structureScore}%`;

      document.getElementById('syntaxScore').textContent = `${syntaxScore.toFixed(0)}%`;
      document.getElementById('syntaxBar').style.width = `${syntaxScore}%`;

      document.getElementById('completenessScore').textContent = `${completenessScore.toFixed(0)}%`;
      document.getElementById('completenessBar').style.width = `${completenessScore}%`;

      // Accuracy & Coverage Summary
      const constructsSummary = document.getElementById('constructsSummary');
      const constructs = metadata.constructs_found || {};

      if (Object.keys(constructs).length > 0) {
        constructsSummary.innerHTML = Object.entries(constructs).map(([name, count]) => `
          <div class="flex items-center gap-2 px-3 py-2 bg-neutral-800 rounded-lg">
            <svg class="w-3 h-3 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            <span class="text-xs text-neutral-300">${name}</span>
            <span class="text-xs text-neutral-500">(${count})</span>
          </div>
        `).join('');
      } else {
        // Infer from conversion level
        const level = data.conversion_level || 1;
        const supportedTypes = [];
        if (level >= 1) supportedTypes.push('Variables', 'Literals', 'Comments');
        if (level >= 2) supportedTypes.push('Functions', 'Conditions', 'Loops');
        if (level >= 3) supportedTypes.push('Complex Expressions');

        constructsSummary.innerHTML = supportedTypes.map(type => `
          <div class="flex items-center gap-2 px-3 py-2 bg-neutral-800 rounded-lg">
            <svg class="w-3 h-3 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            <span class="text-xs text-neutral-300">${type}</span>
          </div>
        `).join('');
      }

      // Add unsupported constructs if any
      const unsupportedConstructs = data.unsupported_constructs || [];
      if (unsupportedConstructs.length > 0) {
        const unsupportedHtml = unsupportedConstructs.slice(0, 5).map(c => `
          <div class="flex items-center gap-2 px-3 py-2 bg-neutral-800/50 border border-neutral-700 rounded-lg">
            <svg class="w-3 h-3 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <span class="text-xs text-neutral-400">${c.construct || c.type || 'Unknown'}</span>
          </div>
        `).join('');
        constructsSummary.innerHTML += unsupportedHtml;
      }

      // Warnings & Recommendations
      const warningsList = document.getElementById('warningsList');
      const warningsSummary = document.getElementById('warningsSummary');
      const warnings = data.warnings || [];

      if (warnings.length > 0) {
        warningsList.innerHTML = warnings.map(w => `
          <div class="flex items-start gap-2 p-2 bg-neutral-800/50 border border-neutral-700 rounded-lg">
            <svg class="w-4 h-4 text-neutral-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <span class="text-sm text-neutral-300">${w}</span>
          </div>
        `).join('');
        warningsSummary.classList.remove('hidden');
      } else {
        warningsList.innerHTML = `
          <p class="text-sm text-neutral-400 flex items-center gap-2">
            <svg class="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
            </svg>
            No major issues detected.
          </p>
        `;
        warningsSummary.classList.add('hidden');
      }

      // Metadata
      document.getElementById('metaLinesProcessed').textContent = linesProcessed || '--';
      document.getElementById('metaBlocksDetected').textContent = blocksDetected || '--';
      document.getElementById('metaConversionLevel').textContent = data.conversion_level || '--';
      document.getElementById('metaConversionTime').textContent = data._conversionTime ? `${data._conversionTime}s` : '--';

      // Unsupported constructs in metadata
      const metaUnsupported = document.getElementById('metaUnsupported');
      const unsupportedList = document.getElementById('unsupportedList');
      if (unsupportedConstructs.length > 0) {
        metaUnsupported.classList.remove('hidden');
        unsupportedList.innerHTML = unsupportedConstructs.map(c =>
          `<span class="inline-block px-2 py-1 bg-neutral-800 rounded mr-1 mb-1">${c.construct || c.type || 'Unknown'} (line ${c.line || '?'})</span>`
        ).join('');
      } else {
        metaUnsupported.classList.add('hidden');
      }
    }

    // Toggle metadata section
    function toggleMetadata() {
      const content = document.getElementById('metadataContent');
      const chevron = document.getElementById('metadataChevron');
      content.classList.toggle('expanded');
      chevron.classList.toggle('rotate-180');
    }

    // Utility functions
    function updateStats() {
      document.getElementById('conversionCount').textContent = stats.conversions;
      const successRate = stats.conversions > 0 ? ((stats.successes / stats.conversions) * 100).toFixed(0) : 100;
      document.getElementById('successRate').textContent = successRate + '%';
    }

    function swapLanguages() {
      const fromLang = document.getElementById('fromLanguage');
      const toLang = document.getElementById('toLanguage');
      const sourceCode = document.getElementById('sourceCode');
      const outputCode = document.getElementById('outputCode');

      const tempLang = fromLang.value;
      fromLang.value = toLang.value;
      toLang.value = tempLang;

      const tempCode = sourceCode.value;
      sourceCode.value = outputCode.value;
      outputCode.value = tempCode;

      updateSourceLineCount();
      updateOutputLineCount();
      updateSourceBadge();
      updateTargetBadge();
      updateSourceHighlight();
      updateOutputHighlight();
      showToast('Languages & code swapped!', 'info');
    }

    function copyOutput() {
      const output = document.getElementById('outputCode').value;
      if (!output.trim()) {
        showToast('No code to copy', 'error');
        return;
      }
      navigator.clipboard.writeText(output);
      showToast('Copied to clipboard!');
    }

    function copyAsMarkdown() {
      const sourceCode = document.getElementById('sourceCode').value;
      const outputCode = document.getElementById('outputCode').value;
      const sourceLang = document.getElementById('fromLanguage').value || 'text';
      const targetLang = document.getElementById('toLanguage').value || 'text';

      if (!sourceCode.trim() || !outputCode.trim()) {
        showToast('No code to export', 'error');
        return;
      }

      const sourceName = languageNames[sourceLang] || sourceLang;
      const targetName = languageNames[targetLang] || targetLang;

      const markdown = `## Code Conversion: ${sourceName} -> ${targetName}

### Original Code (${sourceName})
\`\`\`${sourceLang}
${sourceCode}
\`\`\`

### Converted Code (${targetName})
\`\`\`${targetLang}
${outputCode}
\`\`\`

---
*Converted using CodeTransform*
`;

      navigator.clipboard.writeText(markdown);
      showToast('Copied as Markdown!');
    }

    function downloadCode() {
      const code = document.getElementById('outputCode').value;
      const language = document.getElementById('toLanguage').value;

      if (!code.trim()) {
        showToast('No code to download', 'error');
        return;
      }

      const extension = languageToExtension[language] || 'txt';
      const filename = `converted_code.${extension}`;

      const blob = new Blob([code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);

      showToast(`Downloaded as ${filename}`);
    }

    function clearSource() {
      document.getElementById('sourceCode').value = '';
      document.getElementById('fromLanguage').value = '';
      document.getElementById('sourceLanguageBadge').classList.add('hidden');
      updateSourceLineCount();
      updateSourceHighlight();
      showToast('Source cleared', 'info');
    }

    // Code formatting functions
    function formatSourceCode() {
      const textarea = document.getElementById('sourceCode');
      const lang = document.getElementById('fromLanguage').value || 'python';
      textarea.value = formatCode(textarea.value, lang);
      updateSourceLineCount();
      updateSourceHighlight();
      showToast('Code formatted!');
    }

    function formatOutputCode() {
      const textarea = document.getElementById('outputCode');
      const lang = document.getElementById('toLanguage').value || 'javascript';
      textarea.value = formatCode(textarea.value, lang);
      updateOutputLineCount();
      updateOutputHighlight();
      showToast('Code formatted!');
    }

    function formatCode(code, language) {
      if (!code.trim()) return code;

      const lines = code.split('\n');
      const formattedLines = [];
      let indentLevel = 0;
      const indentChar = language === 'python' ? '    ' : '  '; // 4 spaces for Python, 2 for JS

      // Patterns for increasing/decreasing indent
      const increaseIndent = language === 'python'
        ? /:\s*$/  // Python: ends with colon
        : /\{\s*$/; // JS: ends with {

      const decreaseIndent = language === 'python'
        ? /^\s*(elif|else|except|finally|return|pass|break|continue)\b/
        : /^\s*\}/; // JS: starts with }

      const decreaseBeforeWrite = language === 'python'
        ? /^\s*(elif|else|except|finally)\b/
        : /^\s*\}/;

      for (let line of lines) {
        // Trim the line
        const trimmed = line.trim();

        // Skip empty lines but preserve them
        if (!trimmed) {
          formattedLines.push('');
          continue;
        }

        // Check if we need to decrease indent before writing
        if (decreaseBeforeWrite.test(trimmed) && indentLevel > 0) {
          indentLevel--;
        }

        // Add proper indentation
        formattedLines.push(indentChar.repeat(indentLevel) + trimmed);

        // Check if we need to increase indent for next line
        if (increaseIndent.test(trimmed)) {
          indentLevel++;
        }

        // For JS, also decrease after closing brace
        if (language !== 'python' && /^\s*\}/.test(trimmed) && !/\{\s*$/.test(trimmed)) {
          // Already handled above
        }
      }

      return formattedLines.join('\n');
    }

    // History management
    function addToHistory(source, converted, fromLang, toLang, confidence) {
      const entry = {
        id: Date.now(),
        sourcePreview: source.substring(0, 50) + (source.length > 50 ? '...' : ''),
        source,
        converted,
        fromLang,
        toLang,
        confidence,
        timestamp: new Date().toLocaleString()
      };
      history.unshift(entry);
      if (history.length > 20) history.pop();
      localStorage.setItem('codeTransformHistory', JSON.stringify(history));
      renderHistory();
    }

    function renderHistory() {
      const list = document.getElementById('historyList');
      if (history.length === 0) {
        list.innerHTML = '<p class="text-neutral-500 text-sm p-4 text-center">No conversion history yet</p>';
        return;
      }

      list.innerHTML = history.map(h => `
        <div class="history-item p-3 rounded cursor-pointer mb-2 bg-neutral-800 border border-neutral-700" onclick="loadHistoryItem(${h.id})">
          <div class="flex justify-between items-center mb-1">
            <span class="text-xs font-semibold text-white">${languageNames[h.fromLang] || h.fromLang} -> ${languageNames[h.toLang] || h.toLang}</span>
            <span class="text-xs text-neutral-400">${(h.confidence * 100).toFixed(0)}%</span>
          </div>
          <p class="text-xs text-neutral-400 truncate">${h.sourcePreview}</p>
          <p class="text-xs text-neutral-600 mt-1">${h.timestamp}</p>
        </div>
      `).join('');
    }

    function loadHistoryItem(id) {
      const item = history.find(h => h.id === id);
      if (item) {
        document.getElementById('sourceCode').value = item.source;
        document.getElementById('outputCode').value = item.converted;
        document.getElementById('fromLanguage').value = item.fromLang;
        document.getElementById('toLanguage').value = item.toLang;
        updateSourceLineCount();
        updateOutputLineCount();
        updateSourceBadge();
        updateTargetBadge();
        updateSourceHighlight();
        updateOutputHighlight();
        toggleHistory();
        showToast('History item loaded', 'info');
      }
    }

    function toggleHistory() {
      const sidebar = document.getElementById('historySidebar');
      sidebar.classList.toggle('translate-x-full');
    }

    function clearHistory() {
      history = [];
      localStorage.setItem('codeTransformHistory', JSON.stringify(history));
      renderHistory();
      showToast('History cleared', 'info');
    }

    // Auto-detect on blur
    document.getElementById('sourceCode').addEventListener('blur', detectLanguage);

// =========================================================================
// Theme toggle (additive — does not modify any converter logic above)
// =========================================================================
(function initTheme() {
  const stored = localStorage.getItem('codeTransformTheme');
  const prefersLight = stored === 'light';
  if (prefersLight) document.documentElement.classList.add('light-mode');

  document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('themeToggle');
    if (!toggleBtn) return;
    updateThemeIcon(toggleBtn);
    toggleBtn.addEventListener('click', () => {
      document.documentElement.classList.toggle('light-mode');
      const isLight = document.documentElement.classList.contains('light-mode');
      localStorage.setItem('codeTransformTheme', isLight ? 'light' : 'dark');
      updateThemeIcon(toggleBtn);
    });
  });

  function updateThemeIcon(btn) {
    const isLight = document.documentElement.classList.contains('light-mode');
    btn.innerHTML = isLight
      ? '<i data-lucide="moon" class="w-4 h-4"></i>'
      : '<i data-lucide="sun" class="w-4 h-4"></i>';
    if (window.lucide) window.lucide.createIcons();
  }
})();
