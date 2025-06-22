"""
Test cases for the Prompt Generation Tool.
Tests the functionality of converting scripts to image generation prompts.
"""

import pytest
import json
from unittest.mock import Mock, patch
from tools.prompt_tool import (
    generate_prompts, 
    validate_prompts_structure, 
    enhance_prompts,
    analyze_script_for_scenes,
    fix_prompts_structure
)

class TestPromptTool:
    """Test cases for prompt generation functionality."""
    
    def test_analyze_script_for_scenes(self):
        """Test script analysis for scene suggestions."""
        script = "Artificial intelligence is transforming our world. We can see amazing innovations everywhere. Technology helps us solve complex problems. The future looks bright with AI."
        
        analysis = analyze_script_for_scenes(script)
        
        assert analysis["sentence_count"] == 4
        assert analysis["suggested_scenes"] == 4
        assert "see" in analysis["visual_elements"]
        assert analysis["complexity"] in ["low", "medium", "high"]
    
    def test_validate_prompts_structure_valid(self):
        """Test validation with valid prompts structure."""
        valid_prompts = [
            {
                "scene_index": 1,
                "prompt": "A futuristic cityscape with AI-powered buildings and flying cars",
                "mood": "optimistic",
                "key_elements": ["city", "technology", "future"],
                "camera_angle": "wide shot",
                "lighting": "bright daylight"
            },
            {
                "scene_index": 2,
                "prompt": "Scientists working with advanced AI computers in a modern laboratory",
                "mood": "focused",
                "key_elements": ["scientists", "computers", "laboratory"],
                "camera_angle": "medium shot",
                "lighting": "professional lighting"
            }
        ]
        
        result = validate_prompts_structure(valid_prompts)
        assert result["is_valid"] == True
        assert len(result["issues"]) == 0
        assert result["prompt_count"] == 2
    
    def test_validate_prompts_structure_invalid(self):
        """Test validation with invalid prompts structure."""
        invalid_prompts = [
            {
                "scene_index": 1,
                "prompt": "Too short"  # Too short
            },
            {
                "scene_index": 2
                # Missing prompt field
            }
        ]
        
        result = validate_prompts_structure(invalid_prompts)
        assert result["is_valid"] == False
        assert len(result["issues"]) > 0
    
    def test_enhance_prompts(self):
        """Test prompt enhancement functionality."""
        original_prompts = [
            {
                "scene_index": 1,
                "prompt": "A robot in a factory",
                "mood": "industrial",
                "key_elements": ["robot", "factory"],
                "camera_angle": "medium shot",
                "lighting": "industrial lighting"
            }
        ]
        
        enhanced = enhance_prompts(original_prompts, "cinematic")
        
        assert len(enhanced) == 1
        assert "cinematic composition" in enhanced[0]["prompt"]
        assert "high quality" in enhanced[0]["prompt"]
        assert enhanced[0]["style_applied"] == "cinematic"
        assert "technical_specs" in enhanced[0]
        assert enhanced[0]["technical_specs"]["aspect_ratio"] == "16:9"
    
    def test_fix_prompts_structure(self):
        """Test fixing malformed prompts structure."""
        broken_prompts = [
            {
                "scene_index": 1,
                "prompt": "Valid prompt with enough content to pass validation"
            },
            {
                "scene_index": 2,
                "prompt": "Short"  # Too short, will be fixed
            }
        ]
        
        fixed = fix_prompts_structure(broken_prompts, 3)
        
        assert len(fixed) == 3  # Should pad to expected count
        assert all("prompt" in p for p in fixed)
        assert all("mood" in p for p in fixed)
        assert all(len(p["prompt"]) >= 20 for p in fixed)
    
    @patch('tools.prompt_tool.genai')
    @patch('tools.prompt_tool.storage_manager')
    def test_generate_prompts_success(self, mock_storage, mock_genai):
        """Test successful prompt generation."""
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = '''[
            {
                "scene_index": 1,
                "prompt": "A stunning visualization of artificial intelligence as glowing neural networks",
                "mood": "futuristic",
                "key_elements": ["AI", "neural networks", "technology"],
                "camera_angle": "close-up",
                "lighting": "neon glow"
            },
            {
                "scene_index": 2,
                "prompt": "Modern scientists collaborating with AI systems in a high-tech laboratory",
                "mood": "collaborative",
                "key_elements": ["scientists", "AI systems", "laboratory"],
                "camera_angle": "medium shot",
                "lighting": "bright professional"
            }
        ]'''
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        # Mock storage upload
        mock_storage.upload_text.return_value = {
            "status": "success",
            "gcs_url": "gs://test-bucket/prompts/test.json",
            "public_url": "https://storage.googleapis.com/test-bucket/prompts/test.json"
        }
        
        script = "Artificial intelligence is transforming our world with amazing innovations."
        result = generate_prompts(script)
        
        assert result["status"] == "success"
        assert result["scene_count"] == 2
        assert len(result["prompts"]) == 2
        assert "prompts_url" in result
        assert result["style_used"] == "cinematic"
    
    @patch('tools.prompt_tool.genai')
    def test_generate_prompts_gemini_error(self, mock_genai):
        """Test handling of Gemini API errors."""
        # Mock Gemini to raise an exception
        mock_genai.configure.side_effect = Exception("API Error")
        
        script = "Test script for error handling"
        result = generate_prompts(script)
        
        assert result["status"] == "failed"
        assert "error" in result
        assert "API Error" in result["error"]
    
    def test_different_styles(self):
        """Test different visual styles for prompt enhancement."""
        base_prompt = [{
            "scene_index": 1,
            "prompt": "A person using technology",
            "mood": "neutral",
            "key_elements": ["person", "technology"],
            "camera_angle": "medium shot",
            "lighting": "natural"
        }]
        
        styles = ["cinematic", "realistic", "artistic", "documentary", "commercial"]
        
        for style in styles:
            enhanced = enhance_prompts(base_prompt, style)
            assert enhanced[0]["style_applied"] == style
            assert style in enhanced[0]["prompt"] or "cinematic" in enhanced[0]["prompt"]  # fallback
    
    def test_prompt_length_validation(self):
        """Test that prompts meet length requirements."""
        very_long_prompt = "A" * 600  # Too long
        very_short_prompt = "AI"      # Too short
        good_prompt = "A detailed scene showing artificial intelligence in action with proper length"
        
        prompts = [
            {"scene_index": 1, "prompt": very_long_prompt},
            {"scene_index": 2, "prompt": very_short_prompt},
            {"scene_index": 3, "prompt": good_prompt}
        ]
        
        result = validate_prompts_structure(prompts)
        assert not result["is_valid"]
        assert any("too long" in issue for issue in result["issues"])
        assert any("too short" in issue for issue in result["issues"])

if __name__ == "__main__":
    # Run basic tests
    test = TestPromptTool()
    
    print("Testing script analysis...")
    test.test_analyze_script_for_scenes()
    print("✓ Script analysis test passed")
    
    print("Testing prompt validation...")
    test.test_validate_prompts_structure_valid()
    test.test_validate_prompts_structure_invalid()
    print("✓ Prompt validation tests passed")
    
    print("Testing prompt enhancement...")
    test.test_enhance_prompts()
    print("✓ Prompt enhancement test passed")
    
    print("Testing structure fixing...")
    test.test_fix_prompts_structure()
    print("✓ Structure fixing test passed")
    
    print("Testing different styles...")
    test.test_different_styles()
    print("✓ Style variation test passed")
    
    print("Testing length validation...")
    test.test_prompt_length_validation()
    print("✓ Length validation test passed")
    
    print("\n🎉 All prompt tool tests passed!") 