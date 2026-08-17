from bisect import bisect_right
from typing import Any, List
from analysis.model import AudioAnalysis
from music.model import Song

class StartTimeAnalyzer:

    def __init__(self):
        pass


    def _avg(self, values: List[tuple]|List[int]) -> float:
        """
        Returns weighted average of first values in list of tuples as a 1 point float
        """
        avg_value = 0
        total_weight = 0
        for v in values:
            if isinstance(v, int):
                avg_value += v
                total_weight += 1
            else:
                avg_value += v[0] * v[1]
                total_weight += v[1]
        return round(avg_value / total_weight if total_weight else 0, 2)

    def _closest_lower(self, sorted_list: List[Any], value: float) -> float:
        """
        Returns the closest lower value from a sorted list
        """
        if isinstance(sorted_list[0], tuple):
            sorted_list = [v[0] for v in sorted_list]
        i = bisect_right(sorted_list, value)
        return round(sorted_list[i - 1], 2) if i > 0 else None

    def _wave_to_diff(self, wave: int) -> float:
        """
        Converts waveform value to a difference value
        """
        if wave < 46.875:
            return -5/(wave-50)
        elif wave < 68.125:
            return 8/25*(wave-(335/8))
        else:
            return (-5/(wave-65)) + 10


    def _create_blocks(self, from_list: List[tuple], max_diff: float, compare: bool = False) -> List[tuple]:
        """
        Groups values into blocks based on max_diff
        """
        blocks = []
        temp = set()
        for idx, val in enumerate(from_list):
            if not temp:
                temp.add(val)
                continue
            avg = self._avg(temp)
            if abs(val[0] - avg) > max_diff:
                if compare:
                    if abs(val[0] - (from_list[idx + 1][0] if idx + 1 < len(from_list) else val[0])) > abs(val[0] - avg):
                        temp.add(val)
                        continue
                blocks.append((avg, round(from_list[idx - 1][1], 2)))
                temp.clear()
            temp.add(val)
        blocks.append((self._avg(temp), round(val[1], 2)))
        temp.clear()
        return blocks

    def _group_waveforms(self, song: Song, group_size: int) -> List[tuple]:
        grouped = []
        temp = set()
        i = 0
        waveforms = len(song.waveform)
        grouped_length = song.duration/waveforms*group_size
        for val in song.waveform:
            i += 1
            temp.add(val)
            if i % group_size == 0 or i == waveforms-1:
                grouped.append((self._avg(temp), round(grouped_length/group_size*i, 2)))
                temp.clear()
        return grouped, grouped_length

    def _zoom_in(self, input_list: List[Any], output_list: List[Any], input_interval_length: float, minus: int, plus: int) -> List[Any]:
        # Implementation for zooming in on specific intervals
        index = int(round(input_list[0][1]/input_interval_length)) - 1
        print(f"Zooming in on index: {index}, minus: {minus}, plus: {plus}")
        candidates = []
        max_diff = [0, 0]
        alt_max_diff = [0, 0]
        lower_bound = max(0, index - minus)
        upper_bound = min(len(output_list) - 1, index + plus)
        for idx, val in enumerate(output_list[lower_bound:upper_bound + 1]):
            print(f"Index: {lower_bound + idx}, Value: {val}")
            if isinstance(val, int):
                if lower_bound > 0:
                    diff = round(abs(val - output_list[lower_bound - 1:upper_bound][idx]), 2)
                else:
                    if idx > 0:
                        diff = round(abs(val - output_list[lower_bound:upper_bound + 1][idx - 1]), 2)
                    else:
                        diff = 0
                val = (val, lower_bound + idx)
            else:
                if lower_bound > 0:
                    diff = round(abs(val[0] - output_list[lower_bound - 1:upper_bound][idx][0]), 2)
                else:
                    if idx > 0:
                        diff = round(abs(val[0] - output_list[lower_bound:upper_bound + 1][idx - 1][0]), 2)
                    else:
                        diff = 0
            candidates.append(val)
            if diff > max_diff[0] + self._wave_to_diff(val[0]):
                max_diff = [diff, idx]
            if diff > alt_max_diff[0]:
                alt_max_diff = [diff, idx]
        print(f"Max diff: {max_diff}, Alt max diff: {alt_max_diff}")
        if max_diff is None or max_diff[0] == 0:
            max_diff = alt_max_diff
        if max_diff[1] - 1 >= 0:
            chosen = [candidates[max_diff[1] - 1], candidates[max_diff[1]]]
        else:
            chosen = [candidates[max_diff[1]]]
        return chosen

    def analyze(self, song: Song, beatnet_analysis: AudioAnalysis, librosa_analysis: AudioAnalysis) -> float:
        """
        Estimates best starting time in miliseconds for playing the song
        Calculates based on waveforms of the song
        """
        if not song.waveform:
            return 0

        # Groups waveforms into groups of 10 (approximately 2 seconds) and for each group takes the average waveform
        values_grouped, grouped_length = self._group_waveforms(song, 10)
        print(f"Grouped waveforms: {values_grouped}, grouped length: {grouped_length}")
        # Goes through grouped values and compares each value to the average of the current forming group, when too distinct, adds current forming group to new list and starts forming new group
        small_blocks = self._create_blocks(values_grouped, 5, compare=False)   #5
        print(f"Small blocks: {small_blocks}")
        medium_blocks = self._create_blocks(small_blocks, 10, compare=True)
        print(f"Medium blocks: {medium_blocks}")
        grouped_chosen = self._zoom_in(medium_blocks, values_grouped, grouped_length, 2, 2)
        print(f"Grouped chosen: {grouped_chosen}")
        wave_length = float(song.duration/len(song.waveform))
        wave_chosen = self._zoom_in(grouped_chosen, song.waveform, wave_length, 9, 10)
        wave_chosen_index = int(wave_chosen[0][1])
        waveform_based_start_time = round(wave_chosen_index * wave_length, 2)
        used_analysis = beatnet_analysis if beatnet_analysis.bpm_confidence and (not librosa_analysis.bpm_confidence or beatnet_analysis.bpm_confidence > librosa_analysis.bpm_confidence) else librosa_analysis
        if used_analysis is beatnet_analysis:
            timestamps = [t[0] for t in beatnet_analysis.beat_timestamps]
        else:
            timestamps = librosa_analysis.beat_timestamps
        start_time = self._closest_lower(timestamps, waveform_based_start_time)
        return start_time if start_time is not None else waveform_based_start_time