<?php
// 웹 모니터링 라이브러리 (카페24용)

/**
 * 두 텍스트의 diff 생성 (변경사항 강조)
 */
function generate_diff($old_text, $new_text) {
    // 단어 단위로 분리
    $old_words = text_to_words($old_text);
    $new_words = text_to_words($new_text);
    
    // 간단한 diff 알고리즘
    $changes = compute_diff($old_words, $new_words);
    
    // HTML로 렌더링
    return render_diff_html($changes);
}

/**
 * 텍스트를 단어 배열로 변환
 */
function text_to_words($text) {
    // 한글, 영문, 숫자, 특수문자 단위로 분리
    preg_match_all('/[\p{L}\p{N}]+|[^\p{L}\p{N}\s]+/u', $text, $matches);
    return $matches[0];
}

/**
 * 간단한 diff 알고리즘 (LCS 기반)
 */
function compute_diff($old, $new) {
    $old_len = count($old);
    $new_len = count($new);
    $matrix = array();
    
    // LCS 행렬 생성
    for ($i = 0; $i <= $old_len; $i++) {
        for ($j = 0; $j <= $new_len; $j++) {
            if ($i == 0 || $j == 0) {
                $matrix[$i][$j] = 0;
            } elseif ($old[$i-1] === $new[$j-1]) {
                $matrix[$i][$j] = $matrix[$i-1][$j-1] + 1;
            } else {
                $matrix[$i][$j] = max($matrix[$i-1][$j], $matrix[$i][$j-1]);
            }
        }
    }
    
    // Diff 추적
    $changes = array();
    $i = $old_len;
    $j = $new_len;
    
    while ($i > 0 || $j > 0) {
        if ($i > 0 && $j > 0 && $old[$i-1] === $new[$j-1]) {
            array_unshift($changes, array('type' => 'unchanged', 'text' => $old[$i-1]));
            $i--;
            $j--;
        } elseif ($j > 0 && ($i == 0 || $matrix[$i][$j-1] >= $matrix[$i-1][$j])) {
            array_unshift($changes, array('type' => 'added', 'text' => $new[$j-1]));
            $j--;
        } elseif ($i > 0 && ($j == 0 || $matrix[$i][$j-1] < $matrix[$i-1][$j])) {
            array_unshift($changes, array('type' => 'removed', 'text' => $old[$i-1]));
            $i--;
        }
    }
    
    return $changes;
}

/**
 * Diff를 HTML로 렌더링
 */
function render_diff_html($changes) {
    $html = '<div class="diff-content">';
    
    foreach ($changes as $change) {
        $text = htmlspecialchars($change['text']);
        
        switch ($change['type']) {
            case 'added':
                $html .= '<span class="diff-added" style="background-color: #d4edda; color: #155724; font-weight: bold; padding: 2px 4px; border-radius: 3px;">' . $text . '</span> ';
                break;
            case 'removed':
                $html .= '<span class="diff-removed" style="background-color: #f8d7da; color: #721c24; text-decoration: line-through; padding: 2px 4px; border-radius: 3px;">' . $text . '</span> ';
                break;
            default:
                $html .= '<span>' . $text . '</span> ';
        }
    }
    
    $html .= '</div>';
    return $html;
}

/**
 * 컨텐츠 해시 생성
 */
function generate_hash($content) {
    return hash('sha256', $content);
}
?>


