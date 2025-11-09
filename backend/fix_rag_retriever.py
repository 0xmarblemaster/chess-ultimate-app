#!/usr/bin/env python3
"""
Fix RAG Retriever to Search ChessLessonChunk for Education Content
"""

import sys
import os
import shutil

def fix_retriever_agent():
    """Fix the retriever agent to search ChessLessonChunk for lesson queries"""
    try:
        print("🔧 FIXING RAG RETRIEVER TO SEARCH RUSSIAN EDUCATION DATA")
        print("=" * 60)
        
        # Backup the original file
        original_file = "etl/agents/retriever_agent.py"
        backup_file = "etl/agents/retriever_agent.py.backup"
        
        print(f"📦 Creating backup: {backup_file}")
        shutil.copy2(original_file, backup_file)
        
        # Read the current file
        with open(original_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("🔍 Analyzing current retriever configuration...")
        
        # Key fixes needed:
        fixes_applied = []
        
        # Fix 1: Update default class_name parameter in retrieve_semantic method
        old_line = 'class_name: str = "ChessGame"'
        new_line = 'class_name: str = None'  # Let it be determined dynamically
        if old_line in content:
            content = content.replace(old_line, new_line)
            fixes_applied.append("✅ Updated default class_name parameter to None")
        
        # Fix 2: Add logic to determine collection based on query content
        # Find the retrieve_semantic method and add collection selection logic
        retrieve_semantic_start = content.find("def retrieve_semantic(self,")
        if retrieve_semantic_start != -1:
            # Find the logger.info line that starts the method
            method_start = content.find('logger.info(f"RetrieverAgent: Semantic search', retrieve_semantic_start)
            if method_start != -1:
                # Insert collection selection logic before the search
                insertion_point = content.find("# Use the module-level search_weaviate", method_start)
                if insertion_point != -1:
                    collection_logic = '''
        # ENHANCED: Determine collection based on query content
        if class_name is None:
            # Analyze query to determine appropriate collection
            query_lower = query.lower()
            russian_education_keywords = [
                'урок', 'lesson', 'шах', 'мат', 'checkmate', 'check', 
                'документ', 'document', 'книг', 'book', 'обучен', 'education',
                'урок 2', 'lesson 2', 'russian', 'русский'
            ]
            
            # Check if query is about Russian education content
            if any(keyword in query_lower for keyword in russian_education_keywords):
                class_name = "ChessLessonChunk"
                logger.info(f"🎓 Detected education query, using ChessLessonChunk collection")
            else:
                class_name = "ChessGame"
                logger.info(f"🎮 Using default ChessGame collection")
        
        '''
                    content = content[:insertion_point] + collection_logic + content[insertion_point:]
                    fixes_applied.append("✅ Added dynamic collection selection logic")
        
        # Fix 3: Update the retrieve method to set target_class_name dynamically
        retrieve_method_start = content.find("def retrieve(self, query: str, metadata: Dict[str, Any])")
        if retrieve_method_start != -1:
            # Find the target_class_name assignment
            target_class_line = 'target_class_name = metadata.get("target_class_name", "ChessGame")'
            if target_class_line in content:
                new_target_logic = '''        # ENHANCED: Determine target class based on query content
        default_class = self._determine_collection_for_query(query)
        target_class_name = metadata.get("target_class_name", default_class)'''
                content = content.replace(target_class_line, new_target_logic)
                fixes_applied.append("✅ Updated retrieve method collection selection")
        
        # Fix 4: Add helper method to determine collection
        # Find the end of the RetrieverAgent class and add the helper method
        class_end = content.rfind("class RetrieverAgent:")
        if class_end != -1:
            # Find a good insertion point (before the last method ends)
            last_method_end = content.rfind("        # client.close() removed - Weaviate client manages connections automatically")
            if last_method_end != -1:
                insertion_point = content.find("\n", last_method_end) + 1
                helper_method = '''
    def _determine_collection_for_query(self, query: str) -> str:
        """Determine which Weaviate collection to search based on query content"""
        query_lower = query.lower()
        
        # Russian education keywords that indicate lesson content
        education_keywords = [
            'урок', 'lesson', 'шах', 'мат', 'checkmate', 'check', 
            'документ', 'document', 'книг', 'book', 'обучен', 'education',
            'урок 2', 'lesson 2', 'russian', 'русский', 'защит', 'defense',
            'тактик', 'tactics', 'стратег', 'strategy', 'диаграмм', 'diagram'
        ]
        
        # Check if query contains education-related keywords
        if any(keyword in query_lower for keyword in education_keywords):
            logger.info(f"🎓 Query '{query}' detected as education content - using ChessLessonChunk")
            return "ChessLessonChunk"
        else:
            logger.info(f"🎮 Query '{query}' detected as game content - using ChessGame")
            return "ChessGame"

'''
                content = content[:insertion_point] + helper_method + content[insertion_point:]
                fixes_applied.append("✅ Added _determine_collection_for_query helper method")
        
        # Write the updated content
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("\n📋 FIXES APPLIED:")
        for fix in fixes_applied:
            print(f"   {fix}")
        
        if not fixes_applied:
            print("   ⚠️  No fixes were applied - check if code structure has changed")
        
        print(f"\n✅ RETRIEVER AGENT UPDATED!")
        print(f"   Original backed up to: {backup_file}")
        print(f"   Now supports both ChessGame and ChessLessonChunk collections")
        print(f"   Russian education queries will automatically use ChessLessonChunk")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing retriever agent: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_retriever_agent() 