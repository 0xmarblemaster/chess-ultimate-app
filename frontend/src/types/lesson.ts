/**
 * Lesson type definitions for the learning platform
 */

export type LessonType = 'theory' | 'exercise' | 'practice';

export type ExerciseType =
  | 'one_move_puzzle'
  | 'multi_move'
  | 'position_eval'
  | 'opening_practice';

/**
 * Base lesson interface
 */
export interface Lesson {
  id: string;
  courseId: string;
  title: string;
  content: string;
  lessonType: LessonType;
  orderNum: number;
  createdAt: string;
  updatedAt: string;

  // Exercise fields (optional)
  exerciseFen?: string | null;
  solutionMove?: string | null;
  exerciseType?: ExerciseType | null;
  hintText?: string | null;
  successMessage?: string | null;
}

/**
 * Exercise lesson with required exercise fields
 */
export interface ExerciseLesson extends Lesson {
  exerciseFen: string;
  solutionMove: string;
  exerciseType: ExerciseType;
  hintText?: string | null;
  successMessage?: string | null;
}

/**
 * Type guard to check if a lesson is an exercise
 */
export function isExerciseLesson(lesson: Lesson): lesson is ExerciseLesson {
  return !!(
    lesson.exerciseFen &&
    lesson.solutionMove &&
    lesson.lessonType === 'exercise'
  );
}

/**
 * API response format for lessons (snake_case from backend)
 */
export interface LessonApiResponse {
  id: string;
  course_id: string;
  title: string;
  content: string;
  lesson_type: 'theory' | 'exercise' | 'practice';
  order_num: number;
  created_at: string;
  updated_at: string;

  // Exercise fields
  exercise_fen?: string | null;
  solution_move?: string | null;
  exercise_type?: string | null;
  hint_text?: string | null;
  success_message?: string | null;
}

/**
 * Convert API response to Lesson type
 */
export function apiResponseToLesson(response: LessonApiResponse): Lesson {
  return {
    id: response.id,
    courseId: response.course_id,
    title: response.title,
    content: response.content,
    lessonType: response.lesson_type,
    orderNum: response.order_num,
    createdAt: response.created_at,
    updatedAt: response.updated_at,
    exerciseFen: response.exercise_fen,
    solutionMove: response.solution_move,
    exerciseType: response.exercise_type as ExerciseType,
    hintText: response.hint_text,
    successMessage: response.success_message,
  };
}
