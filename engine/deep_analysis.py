# /RustForge/engine/deep_analysis.py
# RustForge Deep Analysis Engine
# Created By: David Kistner (Unconditional Love) at GlyphicMind Solutions LLC.



# system imports
from typing import List, Optional, Dict, Any



# ==================================
# DEEP ANALYSIS ENGINE CLASS
# ==================================
class DeepAnalysisEngine:
    """
    Deep Analysis Engine v2 for RustForge

    Pipeline:
    - Chunk → Summarize (fast model or same model)
    - Meta-summarize (fast model or same model)
    - Final rewrite (smart model or same model)

    Focused on Rust structure:
    - crates, modules, files
    - use/imports
    - structs, enums, traits
    - impl blocks, functions, methods
    - ownership, lifetimes (at a high level)

    Dependencies:
    - prompt_builder with:
        - build_prompt(topic, model_key)
    - llm_engine with:
        - generate(prompt, model_key)
    """

    # --------------
    # Initialize
    # --------------
    def __init__(
        self,
        prompt_builder,
        llm_engine,
        model_fast: str,
        model_smart: str,
        chunk_size: int = 4000,
        debug: bool = False,
    ):
        self.prompt_builder = prompt_builder
        self.llm = llm_engine
        self.model_fast = model_fast
        self.model_smart = model_smart
        self.chunk_size = chunk_size
        self.debug = debug

        # internal event log
        self.events: List[Dict[str, Any]] = []


# ============================= #
# Logging Section               #
# ============================= #
    # -------------
    # Log
    # -------------
    def _log(self, stage: str, message: str, extra: Optional[Dict[str, Any]] = None):
        entry = {"stage": stage, "message": message}
        if extra:
            entry.update(extra)
        self.events.append(entry)
        if self.debug:
            print(f"[RustDeepAnalysis:{stage}] {message}")

    # -------------
    # Get Log
    # -------------
    def get_log(self) -> List[Dict[str, Any]]:
        return list(self.events)

    # ---------------
    # Safe Generate
    # ---------------
    def _safe_generate(self, prompt: str, model_key: str, stage: str) -> str:
        try:
            raw = self.llm.generate(prompt, model_key=model_key)
            if not raw or not str(raw).strip():
                self._log(stage, "LLM returned empty output.", {"model_key": model_key})
                return ""
            return str(raw).strip()
        except FileNotFoundError as e:
            self._log(stage, "Model file not found.", {"model_key": model_key, "error": str(e)})
            return ""
        except Exception as e:
            self._log(stage, "LLM generate failed.", {"model_key": model_key, "error": str(e)})
            return ""


# ============================== #
# Helpers                        #
# ============================== #
    # -------------
    # Chunk Code
    # -------------
    def chunk_code(self, code: str) -> List[str]:
        chunks = []
        while code:
            chunks.append(code[: self.chunk_size])
            code = code[self.chunk_size :]
        self._log("chunk_code", "Code chunked.", {"chunk_count": len(chunks)})
        return chunks


# =============================== #
# Summarising Section             #
# =============================== #
    # ----------------
    # Summarize Chunk
    # ----------------
    def summarize_chunk(self, chunk: str, index: int, total: int) -> str:
        topic = (
            "Summarize this Rust code for later reconstruction. "
            "Focus on crate layout, modules, use/imports, structs, enums, traits, "
            "impl blocks, functions, methods, and logic flow:\n\n"
            f"{chunk}"
        )

        prompt = self.prompt_builder.build_prompt(topic, self.model_fast)
        self._log("summarize_chunk", "Summarizing chunk.", {"index": index + 1, "total": total})

        raw = self._safe_generate(prompt, model_key=self.model_fast, stage="summarize_chunk")

        if not raw:
            fallback = f"[Summary unavailable for chunk {index + 1}/{total}]"
            self._log("summarize_chunk", "Using fallback summary.", {"index": index + 1})
            return fallback

        return raw

    # -----------------
    # Merge Summaries
    # -----------------
    def merge_summaries(self, summaries: List[str]) -> str:
        joined = "\n\n--- SUMMARY BREAK ---\n\n".join(summaries)

        topic = (
            "Merge these Rust code summaries into a single, coherent project summary. "
            "Describe crate structure, modules, use/imports, structs, enums, traits, "
            "impl blocks, functions, methods, and overall architecture:\n\n"
            f"{joined}"
        )

        prompt = self.prompt_builder.build_prompt(topic, self.model_fast)
        self._log("merge_summaries", "Merging summaries.", {"summary_count": len(summaries)})

        raw = self._safe_generate(prompt, model_key=self.model_fast, stage="merge_summaries")

        if not raw:
            self._log("merge_summaries", "Using joined summaries as meta-summary fallback.")
            return joined

        return raw

    # ----------------------
    # Analyze From Summary
    # ----------------------
    def analyze_from_summary(self, meta_summary: str) -> str:
        topic = (
            "Using ONLY this project summary, reconstruct or refactor the Rust code. "
            "Preserve logic, improve structure, respect idiomatic Rust patterns, and output ONLY Rust code. "
            "If multiple files or modules are implied, use // FILE: markers such as "
            "src/main.rs, src/lib.rs, src/module/mod.rs:\n\n"
            f"{meta_summary}"
        )

        prompt = self.prompt_builder.build_prompt(topic, self.model_smart)
        self._log("analyze_from_summary", "Reconstructing code from meta-summary.")

        raw = self._safe_generate(prompt, model_key=self.model_smart, stage="analyze_from_summary")

        if not raw:
            self._log("analyze_from_summary", "Reconstruction failed or empty.")
            return ""

        return raw


# =============================== #
# Run Pipeline Section            #
# =============================== #
    # -------------
    # Run
    # -------------
    def run(self, code: str) -> str:
        self.events.clear()
        self._log("run_start", "Rust Deep Analysis v2 run started.")

        if not code or not code.strip():
            self._log("run_abort", "Empty code input; returning original.")
            return code

        chunks = self.chunk_code(code)
        if not chunks:
            self._log("run_abort", "No chunks produced; returning original.")
            return code

        summaries = []
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            summaries.append(self.summarize_chunk(chunk, index=idx, total=total))

        meta = self.merge_summaries(summaries)
        if not meta or not meta.strip():
            self._log("run_fallback", "Meta-summary empty; returning original code.")
            return code

        corrected = self.analyze_from_summary(meta)
        if not corrected or not corrected.strip():
            self._log("run_fallback", "Corrected code empty; returning original code.")
            return code

        self._log("run_complete", "Rust Deep Analysis v2 completed successfully.")
        return corrected

