"use server";
import { tavily} from '@tavily/core';

const tvly = process.env.TAVILY_API_KEY
  ? tavily({ apiKey: process.env.TAVILY_API_KEY })
  : null;


type TavilySearchResult = {
    title: string;
    url: string;
    content: string;
    rawContent?: string;
    score: number;
    publishedDate: string;
};

export async function searchWebAnswer(searchQuery: string) {
    if (!tvly) {
        throw new Error('Web search is not available. TAVILY_API_KEY environment variable is not set.');
    }

    const res = await tvly.search(searchQuery, { searchDepth: 'basic', includeAnswer: true, includeImages: false });

    const resultsWithUrls = res.results
        .map((result: TavilySearchResult, idx: number) => `${idx + 1}. ${result.title}\n${result.url}`)
        .join('\n\n');

    return `Answer: ${res.answer}\n\n${resultsWithUrls}`;
}
